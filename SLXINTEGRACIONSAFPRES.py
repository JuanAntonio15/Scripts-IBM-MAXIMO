#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 27-09-2021
#Descripción: Integración con el sistema externo SAF para presupuesto

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer
from java.util import HashMap, Date
from psdi.iface.router import HTTPHandler
from java.text import SimpleDateFormat
from com.ibm.json.java import JSONObject

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO SLXINTEGRACIONSAFPRES*********************")
mxserver = MXServer.getMXServer()
userinfo = mxserver.getSystemUserInfo()
fechaActual = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(Date())

#URL
URL_LOGIN = "https://172.25.2.39:15024/api/autenticacion/login"
URL_PRESUPUESTO = "https://172.25.2.39:15024/api/Presupuesto"

#FUNCIÓN REUTILIZABLE QUE PERMITE INVOCAR LA API DE SAF DESDE LOS DISTINTOS ESCENARIOS DE MAXIMO
def invocarApi(url, codigoJson, token):
    logger.debug("*******************FUNC. INVOCAR API - INICIO")
    handler = HTTPHandler()
    map = errorResponse = HashMap()
    map.put("URL",url)
    map.put("HTTPMETHOD","POST")
    map.put("ERRORONSTATUS",False)
    map.put("RESPONSE_HEADERS",errorResponse)
    map.put("HEADERS","Content-Type:application/json, Authorization: "+token) if token is not None else map.put("HEADERS","Content-Type:application/json")
    map.put("HTTPEXIT", "com.epp.iface.saf.ProcessResponseExit")
    responseHandler = handler.invoke(map,codigoJson)
    response = "".join([chr(item) for item in responseHandler])
    responseStatus = int(errorResponse.get("RESPONSE_STATUS"))
    responseStatusText = (errorResponse.get("RESPONSE_STATUS_TEXT")).encode("utf-8")   
    logger.debug("*******************CODIGO RESP: "+str(responseStatus))
    logger.debug("*******************MENSAJE RESP: "+str(responseStatusText))
    logger.debug("*******************RESP: "+str(response))
    logger.debug("*******************FUNC. INVOCAR API - FIN")
    return responseStatus, responseStatusText, response
	
#FUNCIÓN ENCARGADA DE OBTENER EL TOKEN DESDE SAF
def obtenerToken():
    logger.debug("*********************FUNC. OBTENER TOKEN - INICIO")
    codigoLogin = "{\"strUsuario\": \"SAFWS_CNX\",\"strPassword\": \"desar\",\"strDominioLdap\": \"B_EEP\"}"
    responseStatus, responseStatusText, response = invocarApi(URL_LOGIN, codigoLogin, None)
    token = response[1:len(response) - 1]
    logger.debug("*********************FUNC. OBTENER TOKEN - FIN") 
    return token

#FUNCIÓN QUE PERMITE OBTENER INFORMACIÓN DEL PROYECTO
def obtenerInfoProyecto(mboLinea):
    logger.debug("*******************FUNC INFO PROYECTO - INICIO")
    area, vigencia, proyecto = "", "", ""
    proyectoMbo = (mboLinea.getMboSet("SLXFINCNTRL")).moveFirst()
    fincntrlSet = mxserver.getMboSet("FINCNTRL", userinfo)
    fincntrlSet.setWhere("PROJECTID='"+proyectoMbo.getString("PROJECTID")+"' AND SLXAR IS NOT NULL AND SLXVI IS NOT NULL AND SLXPR IS NOT NULL")
    if not fincntrlSet.isEmpty():
        fincntrl = fincntrlSet.moveFirst()
        area = fincntrl.getString("SLXAR")
        vigencia = fincntrl.getInt("SLXVI")
        proyecto = fincntrl.getString("SLXPR")
    logger.debug("*******************FUNC INFO PROYECTO - FIN")		
    return area, vigencia, proyecto

#FUNCIÓN QUE PERMITE OBTENER INFORMACIÓN DEL CONTRATO
def obtenerInfoContrato(mbo):
    logger.debug("*******************FUNC INFO CONTRATO - INICIO")
    slxconcon3 = ""
    purchviewSet = mxserver.getMboSet("PURCHVIEW", userinfo)
    purchviewSet.setWhere("CONTRACTNUM='"+mbo.getString("SLXCONTRATO")+"' AND STATUS='APPR'")
    if not purchviewSet.isEmpty():
        purchview = purchviewSet.moveFirst()
        slxconcon3 = purchview.getString("SLXCONCON3")
    return slxconcon3
    logger.debug("*******************FUNC INFO CONTRATO - FIN")

#SLXCONCON3
#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE PRLINE
def asignarLineasPR(prLineSet):
    logger.debug("*******************FUNC ASIGNAR LINEAS - INICIO")
    codigoLineas, primerArea = "", ""
    prline = prLineSet.moveFirst()
    indice = 1
    while(prline is not None):
        primerArea, vigencia, proyecto = obtenerInfoProyecto(prline)
        logger.debug("*******************AREA: "+str(primerArea))
        desc = prline.getString("DESCRIPTION")
        decValor = prline.getDouble("LINECOST") + prline.getDouble("TAX1") + prline.getDouble("TAX2")
        if indice < prLineSet.count():
            codigoLineas = codigoLineas + "{\"datFechaMov\": \""+fechaActual+"\", \"srtCtaPpto\": \""+prline.getString("FCTASKID")+"\", \"strArea\": \""+primerArea+"\", \"strProyecto\": \""+proyecto+"\", \"decValor\": "+str(decValor)+", \"strDescripcion\": \""+desc.replace("\"","\\\"")+"\", \"strTpDocDis\": \"\", \"strNrDocDis\": \"\", \"decVgDocDis\": \""+str(vigencia)+"\"},"
        else:
            codigoLineas = codigoLineas + "{\"datFechaMov\": \""+fechaActual+"\", \"srtCtaPpto\": \""+prline.getString("FCTASKID")+"\", \"strArea\": \""+primerArea+"\", \"strProyecto\": \""+proyecto+"\", \"decValor\": "+str(decValor)+", \"strDescripcion\": \""+desc.replace("\"","\\\"")+"\", \"strTpDocDis\": \"\", \"strNrDocDis\": \"\", \"decVgDocDis\": \""+str(vigencia)+"\"}"
        indice += 1
        prline = prLineSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS - FIN")
    return codigoLineas, primerArea

#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE POLINE
def asignarLineasPO(poLineSet, slxdpr):
    logger.debug("*******************FUNC ASIGNAR LINEAS - INICIO")
    codigoLineas, primerArea = "", ""
    poline = poLineSet.moveFirst()
    indice = 1
    while(poline is not None):
        primerArea, vigencia, proyecto = obtenerInfoProyecto(poline)
        desc = poline.getString("DESCRIPTION")
        decValor = poline.getDouble("LINECOST") + poline.getDouble("TAX1") + poline.getDouble("TAX2")
        if indice < poLineSet.count():
            codigoLineas = codigoLineas + "{\"datFechaMov\": \""+fechaActual+"\", \"srtCtaPpto\": \""+poline.getString("FCTASKID")+"\", \"strArea\": \""+primerArea+"\", \"strProyecto\": \""+proyecto+"\", \"decValor\": "+str(decValor)+", \"strDescripcion\": \""+desc.replace("\"","\\\"")+"\", \"strTpDocDis\": \"DPR\", \"strNrDocDis\": \""+slxdpr+"\", \"decVgDocDis\": \""+str(vigencia)+"\"},"
        else:
            codigoLineas = codigoLineas + "{\"datFechaMov\": \""+fechaActual+"\", \"srtCtaPpto\": \""+poline.getString("FCTASKID")+"\", \"strArea\": \""+primerArea+"\", \"strProyecto\": \""+proyecto+"\", \"decValor\": "+str(decValor)+", \"strDescripcion\": \""+desc.replace("\"","\\\"")+"\", \"strTpDocDis\": \"DPR\", \"strNrDocDis\": \""+slxdpr+"\", \"decVgDocDis\": \""+str(vigencia)+"\"}"			
        indice += 1
        poline = poLineSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS - FIN")
    return codigoLineas, primerArea

#PRESUPUESTO DE LA SOLICITUD DE COMPRA (PR)
if launchPoint == "PR":
    logger.debug("*********************SOLICITUD DE COMPRA - INICIO")
    prLineSet = mbo.getMboSet("PRLINE")
    if status_modified and status == "APROBADA" and prLineSet.isEmpty() is False and mbo.isNull("SLXDPR"):
        token = obtenerToken()
        fechaRequerida = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(mbo.getDate("REQUIREDDATE")) if not mbo.isNull("REQUIREDDATE") else ""
        desc = "SOLICITUD:"+mbo.getString("PRNUM")+"/PLANTA:"+mbo.getString("SITEID")+"/"+mbo.getString("DESCRIPTION")
        vendor = mbo.getString("VENDOR") if not mbo.isNull("VENDOR") else "1"
        lineasPR, slxarea = asignarLineasPR(prLineSet)		
        codigoPR = "{\"strClase\": \"D\", \"strTipoDoc\": \"\", \"strNroDoc\": \"\", \"datFecha\":\""+fechaActual+"\", \"strConcepto\": \""+desc.replace("\"","\\\"")+"\", \"lnAuxiliar\": "+str(vendor)+",\"datFechaVto\": \""+fechaRequerida+"\", \"strArea\": \""+slxarea+"\", \"lisMovimientos\": ["+lineasPR+"]}"
        logger.debug("*******************CODIGO PR: "+str(codigoPR.encode("utf-8")))				
        responseStatus, responseStatusText, response = invocarApi(URL_PRESUPUESTO, codigoPR.encode("utf-8"), token)
        presupuestoPRJSON = JSONObject.parse(response)
        mbo.setValue("SLXDPR", presupuestoPRJSON.get("strNroDoc"), 11L)
        mbo.setValue("PR1", presupuestoPRJSON.get("strNroDoc"), 11L)
        mbo.setValue("SLXTIPODOC", presupuestoPRJSON.get("strTipoDoc"), 11L)
        logger.debug("*******************GUARDADO EN SLXDPR")
    logger.debug("*********************SOLICITUD DE COMPRA - FIN")

#PRESUPUESTO DE LA ORDEN DE COMPRA (PO)
elif launchPoint == "PO":
    logger.debug("*********************ORDEN DE COMPRA - INICIO")
    poLineSet = mbo.getMboSet("POLINE")
    if status_modified and status == "APROB" and poLineSet.isEmpty() is False:
        if not mbo.isNull("SLXDPR"):
            token = obtenerToken()
            fechaRequerida = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(mbo.getDate("REQUIREDDATE")) if not mbo.isNull("REQUIREDDATE") else ""
            desc = "ORDEN:"+mbo.getString("PONUM")+"/PLANTA:"+mbo.getString("SITEID")+"/"+mbo.getString("DESCRIPTION")
            vendor = mbo.getString("VENDOR") if not mbo.isNull("VENDOR") else "null"
            lineasPO, slxarea = asignarLineasPO(poLineSet, mbo.getString("SLXDPR"))
            slxconcon3 = obtenerInfoContrato(mbo)
            codigoPO = "{\"strClase\": \"R\", \"strTipoDoc\": \""+slxconcon3+"\", \"strNroDoc\": \""+mbo.getString("SLXCONTRATO")+"\", \"datFecha\":\""+fechaActual+"\", \"strConcepto\": \""+desc.replace("\"","\\\"")+"\", \"lnAuxiliar\": "+str(vendor)+",\"datFechaVto\": \""+fechaRequerida+"\", \"strArea\": \""+slxarea+"\", \"lisMovimientos\": ["+lineasPO+"]}"
            logger.debug("*******************CODIGO PO: "+str(codigoPO.encode("utf-8")))				
            responseStatus, responseStatusText, response = invocarApi(URL_PRESUPUESTO, codigoPO.encode("utf-8"), token)
            presupuestoPOJSON = JSONObject.parse(response)
            mbo.setValue("SLXRPR", presupuestoPOJSON.get("strNroDoc"), 11L)
            mbo.setValue("SLXTIPODOC2", presupuestoPOJSON.get("strTipoDoc"), 11L)
            logger.debug("*******************GUARDADO EN SLXRPR")
        else:
            service.error("designer", "generic",[u"Error para enviar el comprobante a SAF. \nCódigo de Error: Interno. \nMensaje: No existe DPR asociado"])
    logger.debug("*********************ORDEN DE COMPRA - FIN")
logger.debug("*********************FIN SLXINTEGRACIONSAFPRES*********************")