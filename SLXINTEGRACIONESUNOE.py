#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 05-10-2021
#Descripción: Integración - Script encargado de consumir las API de integración de UNOE

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer
from java.util import HashMap, Date
from psdi.iface.router import HTTPHandler
from java.text import SimpleDateFormat
from psdi.util import MXException
from com.ibm.json.java import JSONObject

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO*********************")
mxserver = MXServer.getMXServer()
userinfo = mxserver.getSystemUserInfo()
fechaActual = SimpleDateFormat("yyyyMMdd").format(Date())

#URL
URL_LOGIN = "http://192.168.2.104:8080/biodmaximo/login"
URL_REQUISICION = "http://192.168.2.104:8080/biodmaximo/requisiciones"
URL_SOLICITUD = "http://192.168.2.104:8080/biodmaximo/solicitudes"

#FUNCIÓN REUTILIZABLE QUE PERMITE INVOCAR LA API DE UNOE DESDE LOS DISTINTOS ESCENARIOS DE MAXIMO
def invocarApi(url, codigoJson, token):
    logger.debug("*******************FUNC. INVOCAR API - INICIO")
    response = responseStatus = responseStatusText = responseHandler = ""
    handler = HTTPHandler()
    map = errorResponse = HashMap()
    map.put("URL",url)
    map.put("HTTPMETHOD","POST")
    map.put("ERRORONSTATUS",False)
    map.put("RESPONSE_HEADERS",errorResponse)
    map.put("HEADERS","Content-Type:application/json, Authorization: "+token) if token is not None else map.put("HEADERS","Content-Type:application/json")
    
    try:
        responseHandler = handler.invoke(map,codigoJson)	
        response = "".join([chr(item) for item in responseHandler])
        responseStatus = int(errorResponse.get("RESPONSE_STATUS"))
    except MXException as e:
        responseStatus = int(errorResponse.get("RESPONSE_STATUS"))
        responseStatusText = errorResponse.get("RESPONSE_STATUS_TEXT")
        logger.debug("*******************ERROR: %s"%e)
	
    logger.debug("*******************CODIGO RESP: "+str(responseStatus))
    logger.debug("*******************MENSAJE RESP: "+str(responseStatusText))
    logger.debug("*******************RESP: "+str(response))
    logger.debug("*******************FUNC. INVOCAR API - FIN")
    return responseStatus, responseStatusText, response
	
#FUNCIÓN ENCARGADA DE OBTENER EL TOKEN DESDE UNOE
def obtenerToken():
    logger.debug("*********************FUNC. OBTENER TOKEN - INICIO")
    token = ""
    codigoLogin = "{\"username\": \"SERVICE\",\"password\": \"9qKLNDnfwqqnKWyWbFSZ\"}"
    responseStatus, responseStatusText, response = invocarApi(URL_LOGIN, codigoLogin, None)
    if response != "":
        bodyResp = JSONObject.parse(response)
        token = ""+str(bodyResp.get("token"))
        logger.debug("*******************TOKEN: "+str(token))	
    
        if responseStatus >= 400 or token == "":
            service.error("designer", "generic",[u"Error al obtener token desde UNOE. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: Sin token de respuesta"])
    else:
        service.error("designer", "generic",[u"Error al obtener token desde UNOE. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: Sin token de respuesta"])
	logger.debug("*********************FUNC. OBTENER TOKEN - FIN") 
    return token
	
#FUNCIÓN QUE PERMITE OBTENER LA PRIORIDAD EN EL FORMATO DEL SISTEMA EXTERNO
def obtenerPrioridad(woPrioridad):
    prioridad = None
    if woPrioridad == "1":
        prioridad = "P1-03 Dias"
    elif woPrioridad == "2":
        prioridad = "P2-08 Dias"
    elif woPrioridad == "3":
        prioridad = "P3-20 Dias"
    elif woPrioridad == "4":
        prioridad = "P4-45 Dias"
    elif woPrioridad == "5":
        prioridad = "P5-90 Dias"		
    return prioridad
     
#FUNCIÓN ENCARGADA DE OBTENER EL ISSUEUNIT DEL ITEM CORRESPONDIENTE
def obtenerItem(itemnum):
    orderunit = ""
    if itemnum is not None:
        itemSet = mxserver.getMboSet("ITEM", userinfo)
        itemSet.setWhere("ITEMNUM='"+itemnum+"'")
        if not itemSet.isEmpty():
            item = itemSet.moveFirst()
            orderunit = item.getString("ISSUEUNIT")
    return orderunit
	
#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE MATERIALES Y FORMAR LA CADENA JSON
def asignarLineas(wpmatSet, glaccount, slx_unneg):
    logger.debug("*******************FUNC ASIGNAR LINEAS - INICIO")
    codigoMateriales = ""
    logger.debug("*******************WPMATSET: "+str(wpmatSet.count()))
    wpmat = wpmatSet.moveFirst()
    indice = 1
    while(wpmat is not None):
        qty = wpmat.getString("ITEMQTY")
        orderunit = obtenerItem(wpmat.getString("ITEMNUM"))
        bodega = "034" if wpmat.getBoolean("DIRECTREQ") else wpmat.getString("LOCATION")
        desc = wpmat.getString("DESCRIPTION")
        motivo = (glaccount.split("-"))[0]
        centroCosto = (glaccount.split("-"))[1]
        if indice < wpmatSet.count():
            codigoMateriales = codigoMateriales + "{\"Item\":"+wpmat.getString("ITEMNUM")+", \"Bodega\":\""+bodega+"\", \"Unidad_medida\":\""+orderunit+"\", \"Cantidad_base\":\""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Centro_costo\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Unidad_negocio\":\""+slx_unneg+"\"},"
        else:
            codigoMateriales = codigoMateriales + "{\"Item\":"+wpmat.getString("ITEMNUM")+", \"Bodega\":\""+bodega+"\", \"Unidad_medida\":\""+orderunit+"\", \"Cantidad_base\":\""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Centro_costo\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Unidad_negocio\":\""+slx_unneg+"\"}"
        indice += 1
        wpmat = wpmatSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS - FIN")
    return codigoMateriales

#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE MATERIALES EN LA MR Y FORMAR LA CADENA JSON
def asignarLineasMR(mrlineSet, mrnum, siteid, glaccount, slx_unneg):
    logger.debug("*******************FUNC ASIGNAR LINEAS MR - INICIO")
    codigoMateriales = ""
    logger.debug("*******************MRLINESET: "+str(mrlineSet.count()))
    mrline = mrlineSet.moveFirst()
    indice = 1	
    while(mrline is not None):
        qty = mrline.getString("QTY")
        orderunit = obtenerItem(mrline.getString("ITEMNUM"))
        desc = mrline.getString("DESCRIPTION")
        motivo = (glaccount.split("-"))[0]
        centroCosto = (glaccount.split("-"))[1]
		
        if indice < mrlineSet.count():
            codigoMateriales = codigoMateriales + "{\"Item\":"+mrline.getString("ITEMNUM")+", \"Bodega\":\""+mrline.getString("STORELOC")+"\", \"Unidad_medida\":\""+orderunit+"\", \"Cantidad_base\":\""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Centro_costo\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Unidad_negocio\":\""+slx_unneg+"\"},"
        else:
            codigoMateriales = codigoMateriales + "{\"Item\":"+mrline.getString("ITEMNUM")+", \"Bodega\":\""+mrline.getString("STORELOC")+"\", \"Unidad_medida\":\""+orderunit+"\", \"Cantidad_base\":\""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Centro_costo\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Unidad_negocio\":\""+slx_unneg+"\"}"
        indice += 1
        mrline = mrlineSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS MR - FIN")
    return codigoMateriales
	
#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE SERVICIOS Y FORMAR LA CADENA JSON
def asignarLineasServ(wpservSet, wonum, siteid, glaccount, slx_unneg):
    logger.debug("*******************FUNC ASIGNAR LINEAS - INICIO")
    codigoServicios = ""
    logger.debug("*******************WPSERVSET: "+str(wpservSet.count()))
    wpserv = wpservSet.moveFirst()
    indice = 1
    while(wpserv is not None):
        qty = wpserv.getString("ITEMQTY")
        desc = wpserv.getString("DESCRIPTION")
        motivo = (glaccount.split("-"))[0]
        centroCosto = (glaccount.split("-"))[1]
        if indice < wpservSet.count():
            codigoServicios = codigoServicios + "{\"Centro_costos\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Unidad_medida\":\""+wpserv.getString("ORDERUNIT")+"\", \"Cantidad_pedida\": \""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Item\":"+wpserv.getString("ITEMNUM")+", \"Unidad_negocio\":\""+slx_unneg+"\"},"
        else:
            codigoServicios = codigoServicios + "{\"Centro_costos\":\""+centroCosto+"\", \"Motivo\": \""+motivo+"\", \"Proyecto\":\"NA\", \"Unidad_medida\":\""+wpserv.getString("ORDERUNIT")+"\", \"Cantidad_pedida\": \""+qty.replace(".",",")+"\", \"Fecha_documento\":\""+fechaActual+"\", \"Notas\":\"\", \"Descripcion_item\":\""+desc.replace("\"","\\\"")+"\", \"Item\":"+wpserv.getString("ITEMNUM")+", \"Unidad_negocio\":\""+slx_unneg+"\"}"
            
        indice += 1
        wpserv = wpservSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS - FIN")
    return codigoServicios
	
#FUNCIÓN ENCARGADA DE OBTENER LA INFORMACIÓN DE LA OT
def obtenerInfoOT(wonum, siteid):
    description = glaccount = slx_unneg = wopriority = ""
    woMRSet = mxserver.getMboSet("WORKORDER", userinfo)
    woMRSet.setWhere("SITEID='"+siteid+"' AND WONUM='"+wonum+"'")
    if not woMRSet.isEmpty():
        woMR = woMRSet.moveFirst()
        description = woMR.getString("DESCRIPTION")
        glaccount = woMR.getString("GLACCOUNT")
        slx_unneg = woMR.getString("SLX_UNNEG")
        wopriority = woMR.getString("WOPRIORITY")		
    return description, glaccount, slx_unneg, wopriority
	
#ORDEN DE TRABAJO
if launchPoint == "WORKORDER":
    logger.debug("*********************ENVIO DE WORKORDER - INICIO")
    if (status == "OTEM" or status == "OTES") and status_modified and mbo.getBoolean("ISTASK") is False:
        token = obtenerToken()			
        materialRelacionado = mbo.getMboSet("SHOWPLANMATERIAL")
        servicioRelacionado = mbo.getMboSet("SHOWALLPLANSERVICE")
			
        #DATOS OT
        wonum = mbo.getString("WONUM")+",0"
        siteid = mbo.getString("SITEID")
        description = mbo.getString("DESCRIPTION")
        glaccount = mbo.getString("GLACCOUNT")
        slx_unneg = mbo.getString("SLX_UNNEG")			
        prioridad = obtenerPrioridad(mbo.getString("WOPRIORITY"))		
		
        #REQUISICIÓN DE MATERIALES DESDE LA OT. SE FORMATEAN LOS VALORES COMO SON SOLICITADOS POR EL SISTEMA EXTERNO
        if status == "OTEM" and materialRelacionado.isEmpty() is False:
            logger.debug("*********************ENVIO DE REQUISICION DE MATERIALES - INICIO")                				
            lineasMateriales = asignarLineas(materialRelacionado, glaccount, slx_unneg)
            codigoReqMat = "{\"documento\": [{\"Fecha_documento\": \""+fechaActual+"\",\"Notas\":\""+description.replace("\"","\\\"")+"\", \"Documento_Referencia\":\""+siteid+"\"}], \"movimiento\":["+lineasMateriales+"], \"entidad1\":[{\"Informacion_prioridad\": \""+prioridad+"\"}], \"entidad2\":[{\"Informacion_Ot\": \""+wonum+"\"}],\"entidad3\":[{\"Materiales_Adicionales\": \"\"}]}"
            logger.debug("*********************CODIGO: "+str(codigoReqMat.encode('utf-8')))
            responseReqStatus, responseReqStatusText, responseReq = invocarApi(URL_REQUISICION, codigoReqMat.encode('utf-8'), token)

            if responseReq != "":
                respReqMatJSON = JSONObject.parse(responseReq)
                respReqMat = respReqMatJSON.get("result")
                logger.debug("*******************RESP FINAL: "+str(respReqMat))			
                if responseReqStatus >= 400 or (responseReqStatus == 200 and respReqMat is False):
                    service.error("designer", "generic",[u"Error al enviar la Requisición de Materiales desde MAXIMO. \nCódigo de Error: "+str(responseReqStatus)+". \nMensaje: "+str(respReqMat)])
            else:
                service.error("designer", "generic",[u"Error al enviar la Requisición de Materiales desde MAXIMO. \nCódigo de Error: "+str(responseReqStatus)+". \nMensaje: Sin mensaje"])
            logger.debug("*********************ENVIO DE REQUISICION DE MATERIALES - FIN")
		
        #SOLICITUD DE COMPRAS DESDE LA OT. SE FORMATEAN LOS VALORES COMO SON SOLICITADOS POR EL SISTEMA EXTERNO	
        elif status == "OTES" and servicioRelacionado.isEmpty() is False:
            logger.debug("*********************ENVIO DE SOLICITUD DE SERVICIOS - INICIO")
            lineasServicios = asignarLineasServ(servicioRelacionado, mbo.getString("WONUM"), siteid, glaccount, slx_unneg)
            codigoSolServ = "{\"documento\": [{\"Fecha_documento\": \""+fechaActual+"\",\"Notas\":\""+description.replace("\"","\\\"")+"\", \"Documento_Referencia\":\""+siteid+"\"}], \"movimiento\":["+lineasServicios+"], \"entidad1\":[{\"Informacion_prioridad\": \""+prioridad+"\"}], \"entidad2\":[{\"Informacion_Ot\": \""+wonum+"\"}],\"entidad3\":[{\"Materiales_Adicionales\": \"\"}]}"
            logger.debug("*********************CODIGO: "+str(codigoSolServ.encode('utf-8')))
            responseSolStatus, responseSolStatusText, responseSol = invocarApi(URL_SOLICITUD, codigoSolServ.encode('utf-8'), token)		

            if responseSol != "":
                respSolServJSON = JSONObject.parse(responseSol)
                respSolServ = respSolServJSON.get("result")
                logger.debug("*******************RESP FINAL: "+str(respSolServ))				
                if responseSolStatus >= 400 or (responseSolStatus == 200 and respSolServ is False):
                    service.error("designer", "generic",[u"Error al enviar la Solicitud de Servicios desde MAXIMO. \nCódigo de Error: "+str(responseSolStatus)+". \nMensaje: "+str(respSolServ)])
            else:			
                service.error("designer", "generic",[u"Error al enviar la Solicitud de Servicios desde MAXIMO. \nCódigo de Error: "+str(responseSolStatus)+". \nMensaje: Sin mensaje"])
            logger.debug("*********************ENVIO DE SOLICITUD DE SERVICIOS - FIN")      
    logger.debug("*********************ENVIO DE WORKORDER - FIN")

#REQUISICIÓN DE MATERIALES DESDE MR. SE FORMATEAN LOS VALORES COMO SON SOLICITADOS POR EL SISTEMA EXTERNO
elif(launchPoint == "MRWAP"):
    logger.debug("*********************ENVIO DE REQUISICION MATERIALES MR- INICIO")
    materialRelacionado = mbo.getMboSet("MRLINE")
    if status_modified and status == 'APPR' and materialRelacionado.isEmpty() is False:
        token = obtenerToken()		
        mrnum = mbo.getString("MRNUM")
        wonum = mbo.getString("WONUM")+",0"
        siteid = mbo.getString("SITEID")
        description, glaccount, slx_unneg, wopriority = obtenerInfoOT(mbo.getString("WONUM"), siteid)	
        prioridad = obtenerPrioridad(wopriority)        
        lineasMateriales = asignarLineasMR(materialRelacionado, mrnum, siteid, glaccount, slx_unneg)	
        codigoReqMat = "{\"documento\": [{\"Fecha_documento\": \""+fechaActual+"\",\"Notas\":\""+description.replace("\"","\\\"")+"\", \"Documento_Referencia\":\""+siteid+"\"}], \"movimiento\":["+lineasMateriales+"], \"entidad1\":[{\"Informacion_prioridad\": \""+prioridad+"\"}], \"entidad2\":[{\"Informacion_Ot\": \""+wonum+"\"}],\"entidad3\":[{\"Materiales_Adicionales\": \""+mrnum+"\"}]}"
        logger.debug("*********************CODIGO: "+str(codigoReqMat.encode('utf-8')))
        responseReqStatus, responseReqStatusText, responseReq = invocarApi(URL_REQUISICION, codigoReqMat.encode('utf-8'), token)	
        respReqMatJSON = JSONObject.parse(responseReq)
        respReqMat = respReqMatJSON.get("result")
        logger.debug("*******************RESP FINAL: "+str(respReqMat))
				
        if responseReqStatus >= 400 or (responseReqStatus == 200 and respReqMat is False):
            service.error("designer", "generic",[u"Error al enviar la Requisición de Materiales MR desde MAXIMO. \nCódigo de Error: "+str(responseReqStatus)+". \nMensaje: "+str(respReqMat)])
    logger.debug("*********************ENVIO DE REQUISICION MATERIALES MR - FIN")
logger.debug("******************************************")