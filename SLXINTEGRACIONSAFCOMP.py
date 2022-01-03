#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 27-09-2021
#Descripción: Integración con el sistema externo SAF para comprobantes

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer
from java.util import Date
from java.text import SimpleDateFormat
from java.net import URL
from java.io import BufferedReader, InputStreamReader, IOException

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO SLXINTEGRACIONSAFCOMP*********************")
mxserver = MXServer.getMXServer()    
userinfo = mxserver.getSystemUserInfo()
fechaActual = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(Date())

#URL
URL_LOGIN = "https://172.25.2.39:15024/api/autenticacion/login"
URL_COMPROBANTES = "https://172.25.2.39:15024/api/Comprobantes"

#FUNCIÓN REUTILIZABLE QUE PERMITE INVOCAR LA API DE SAF DESDE LOS DISTINTOS ESCENARIOS DE MAXIMO
def invocarApi(urlString, codigoJson, token):
    logger.debug("*******************FUNC. INVOCAR API - INICIO")
    responseStatus, response = "", ""
    try:
        #SE FORMA LA URL Y SE ABRE LA CONEXIÓN. ADEMÁS AGREGAN LAS PROPIEDADES PARA EL LLAMADO
        url = URL(urlString)
        conexion = url.openConnection()
        conexion.setDoOutput(True)
        conexion.setRequestMethod("POST")
        conexion.setRequestProperty("Content-Type", "application/json")
        if token is not None:
            conexion.setRequestProperty("Authorization", token)
        #SE REALIZA EL LLAMADO
        os = conexion.getOutputStream()
        #os.write(codigoJson.encode())
        os.write(codigoJson)
        os.flush()    
        responseStatus = conexion.getResponseCode()
        br = BufferedReader(InputStreamReader(conexion.getInputStream()))
        response = br.readLine()
    except IOException as e:
        responseStatus = conexion.getResponseCode()
        br = BufferedReader(InputStreamReader(conexion.getErrorStream()))
        response = br.readLine()
    logger.debug("*******************CODIGO RESPUESTA: "+str(responseStatus))
    logger.debug("*******************MENSAJE: "+str(response.encode("utf-8")))
    logger.debug("*******************FUNC. INVOCAR API - FIN")
    return responseStatus, response
	
#FUNCIÓN ENCARGADA DE OBTENER EL TOKEN DESDE SAF
def obtenerToken(puntoLanz):
    logger.debug("*********************FUNC. OBTENER TOKEN - INICIO")
    token = ""
    codigoLogin = "{\"strUsuario\": \"SAFWS_CNX\",\"strPassword\": \"desar\",\"strDominioLdap\": \"B_EEP\"}"
    responseStatus, response = invocarApi(URL_LOGIN, codigoLogin, None)
	
    if responseStatus < 400:
        token = response[1:len(response) - 1]
    else:
        mensaje = ""+response if puntoLanz == "WORKORDER" else "Error al obtener token desde SAF. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: "+response
        service.error("designer", "generic",[u""+mensaje])
	logger.debug("*********************FUNC. OBTENER TOKEN - FIN") 
    return token
	
#FUNCIÓN QUE PERMITE ANULAR COMPROBANTES
def anularComprobante(dictRespuestas, token, puntoLanz):
    logger.debug("*********************FUNC. ANULAR COMPROBANTE - INICIO")
    respAnular = True
    if len(dictRespuestas) > 0:
        for tipoComprobante, valores in dictRespuestas.items():   	
            codigoAnular = "{\"intTipoComprobante\":"+str(tipoComprobante)+", \"lngNroComprobante\": "+str(dictRespuestas.get(tipoComprobante)[0])+", \"fechaComprobante\": \""+str(dictRespuestas.get(tipoComprobante)[1])+"\"}"
            logger.debug("*********************CODIGO ANULAR: "+str(codigoAnular.encode("utf-8")))			
            responseAnuStatus, responseAnu = invocarApi(URL_COMPROBANTES, codigoAnular.encode("utf-8"), token)
            mensaje = ""+response if puntoLanz == "WORKORDER" else "Error al anular comprobante desde SAF. \nCódigo de Error: "+str(responseAnuStatus)+". \nMensaje: "+responseAnu
			
            if responseAnuStatus >= 400:
                respAnular = False
                service.error("designer", "generic",[u""+mensaje])
    logger.debug("*********************FUNC. ANULAR COMPROBANTE - FIN")
    return respAnular

#FUNCIÓN QUE PERMITE GUARDAR COMPROBANTES
def guardarComprobante(dictRespuestas):
    logger.debug("*********************FUNC. GUARDAR COMPROBANTE - INICIO")
    if len(dictRespuestas) > 0:
        for tipoComprobante, valores in dictRespuestas.items():
            for invuselineMbo in valores[2]:
                numeroComprobante = dictRespuestas.get(tipoComprobante)[0]				
                invuselineMbo.setValue("SLXIDCOMPROBANTE", "COMP:"+str(tipoComprobante)+"/DCTO:"+str(numeroComprobante), 11L)
    logger.debug("*********************FUNC. GUARDAR COMPROBANTE - FIN")
	
#FUNCIÓN QUE PERMITE ASIGNAR CUENTAS POR SEGMENTO, SI NO TIENE VALOR QUEDA NONE
def asignarCuentas(cuenta):
    cuentaPos0 = cuentaPos1 = ""    
    if(len(cuenta) == 1):
        cuentaPos0 = cuenta[0]
    elif(len(cuenta) == 2):
        cuentaPos0 = cuenta[0]
        cuentaPos1 = cuenta[1]
    return cuentaPos0, cuentaPos1

#VERIFICAR QUE TIPO DE DESPACHO SEGÚN LO ESPECIFICADO
def verificarTipoComprobanteLinea(lineaMbo):
    tipoComprobante = None
    itemSet = mxserver.getMboSet("ITEM", userinfo)
    itemSet.setWhere("ITEMNUM='"+lineaMbo.getString("ITEMNUM")+"'")
		
    if not itemSet.isEmpty():
        item = itemSet.moveFirst()
        if item.getBoolean("ROTATING"):
            tipoComprobante = 40
        elif item.getBoolean("SLX_ESELECTRICO"):
            tipoComprobante = 72
        elif not item.getBoolean("SLX_ESELECTRICO"):
            tipoComprobante = 42
            inventorySet = mxserver.getMboSet("INVENTORY", userinfo)
            inventorySet.setWhere("ITEMNUM='"+lineaMbo.getString("ITEMNUM")+"'")
            if not inventorySet.isEmpty():
                inventory = inventorySet.moveFirst()
                if inventory.getBoolean("CONSIGNMENT"):
                    tipoComprobante = 58
    return tipoComprobante
			
#FUNCIÓN PARA AGRUPAR LOS TIPOS DE UTILIZACIÓN DE LOS ITEMS
def agruparItems(lineaMboSet, puntoLanz):
    listaTransferencias, listaDespachosRot, listaDespachosElect, listaDespachosNoElect, listaDespachosCons, listaDevolucion = ([] for i in range(6))
    lineaMbo = lineaMboSet.moveFirst()
	
    while(lineaMbo is not None):
        type = lineaMbo.getString("ISSUETYPE") if puntoLanz == "WORKORDER" else lineaMbo.getString("USETYPE")
        logger.debug("*********************ITEMNUM: "+str(lineaMbo.getString("ITEMNUM")))
        logger.debug("*********************TYPE: "+str(type))
		
        if type == "TRANSFER":
            listaTransferencias.append(lineaMbo)
        elif type == "ISSUE":
            if verificarTipoComprobanteLinea(lineaMbo) == 40:
                listaDespachosRot.append(lineaMbo)
            elif verificarTipoComprobanteLinea(lineaMbo) == 42:
                listaDespachosNoElect.append(lineaMbo)
            elif verificarTipoComprobanteLinea(lineaMbo) == 58:
                listaDespachosCons.append(lineaMbo)
            elif verificarTipoComprobanteLinea(lineaMbo) == 72:
                listaDespachosElect.append(lineaMbo)
        elif type == "RETURN":
            listaDevolucion.append(lineaMbo)
        lineaMbo = lineaMboSet.moveNext()
    logger.debug("*********************TOTAL TRANSFER: "+str(len(listaTransferencias)))
    logger.debug("*********************TOTAL ISSUE 40: "+str(len(listaDespachosRot)))
    logger.debug("*********************TOTAL ISSUE 42: "+str(len(listaDespachosNoElect)))
    logger.debug("*********************TOTAL ISSUE 58: "+str(len(listaDespachosCons)))
    logger.debug("*********************TOTAL ISSUE 72: "+str(len(listaDespachosElect)))
    logger.debug("*********************TOTAL RETURN: "+str(len(listaDevolucion)))	
    return {77:listaTransferencias, 40: listaDespachosRot, 42:listaDespachosNoElect, 58:listaDespachosCons, 72:listaDespachosElect, 78:listaDevolucion}

#FUNCIÓN ENCARGADA DE DIVIDIR LA LÍNEA DE CRÉDITO Y DÉBITO REQUERIDO POR SAF
def asignarLineas(lista):
    i = 1
    largoLista = len(lista)
    codigoJSON = ""
	
    for invuselineMbo in lista:
        cuentaContableD, centroCostoD = asignarCuentas((invuselineMbo.getString("GLDEBITACCT")).split("-"))
        cuentaContableC, centroCostoC = asignarCuentas((invuselineMbo.getString("GLCREDITACCT")).split("-"))
        lineaDebito = "{\"intNroRenglon\": "+str(i)+",\"strCuentaContable\":\""+cuentaContableD+"\",\"lngNit\":\"1\",\"strClaseMovimiento\": \"D\",\"decValorMovimiento\": "+str(invuselineMbo.getDouble("LINECOST"))+",\"strDescripcion\": \""+(invuselineMbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoD+"\"},"
        lineaCredito = "{\"intNroRenglon\": "+str(i+1)+",\"strCuentaContable\":\""+cuentaContableC+"\",\"lngNit\":\"1\",\"strClaseMovimiento\": \"C\",\"decValorMovimiento\": -"+str(invuselineMbo.getDouble("LINECOST"))+",\"strDescripcion\": \""+(invuselineMbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoC+"\"}"

        if largoLista > 1:
            lineaCredito = lineaCredito + ","

        codigoJSON = codigoJSON + lineaDebito + lineaCredito
        largoLista -=1
        i+=2
    return codigoJSON

#FUNCIÓN ENCARGADA DE DIVIDIR LA LÍNEA DE CRÉDITO Y DÉBITO REQUERIDO POR SAF
def asignarLineasRecepcion(mbo):
    vendor = cuentaDebito = lineaDebito = lineaCredito = ""
    ponumSet = mbo.getMboSet("PO")
    if not ponumSet.isEmpty():
        vendor = (ponumSet.moveFirst()).getString("VENDOR")

    polineSet = mbo.getMboSet("POLINE")
    if not polineSet.isEmpty():
        cuentaDebito = (polineSet.moveFirst()).getString("GLDEBITACCT")
    #cuentaContableD, centroCostoD = asignarCuentas((mbo.getString("GLDEBITACCT")).split("-"))
    cuentaContableD, centroCostoD = asignarCuentas(cuentaDebito.split("-"))
    cuentaContableC, centroCostoC = asignarCuentas((mbo.getString("GLCREDITACCT")).split("-"))

    if mbo.getString("ISSUETYPE") == "RETURN":
        lineaDebito = "{\"intNroRenglon\": 1,\"strCuentaContable\":\""+cuentaContableD+"\",\"lngNit\":\""+vendor+"\",\"strClaseMovimiento\": \"D\",\"decValorMovimiento\": "+str(mbo.getDouble("LOADEDCOST")*-1)+",\"strDescripcion\": \""+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoD+"\"},"
        lineaCredito = "{\"intNroRenglon\": 2,\"strCuentaContable\":\""+cuentaContableC+"\",\"lngNit\":\""+vendor+"\",\"strClaseMovimiento\": \"C\",\"decValorMovimiento\": "+str(mbo.getDouble("LOADEDCOST"))+",\"strDescripcion\": \""+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoC+"\"}"
    else:
        lineaDebito = "{\"intNroRenglon\": 1,\"strCuentaContable\":\""+cuentaContableD+"\",\"lngNit\":\""+vendor+"\",\"strClaseMovimiento\": \"D\",\"decValorMovimiento\": "+str(mbo.getDouble("LOADEDCOST"))+",\"strDescripcion\": \""+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoD+"\"},"
        lineaCredito = "{\"intNroRenglon\": 2,\"strCuentaContable\":\""+cuentaContableC+"\",\"lngNit\":\""+vendor+"\",\"strClaseMovimiento\": \"C\",\"decValorMovimiento\": "+str(mbo.getDouble("LOADEDCOST")*-1)+",\"strDescripcion\": \""+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\", \"strCentroCosto\":\""+centroCostoC+"\"}"
    return lineaDebito + lineaCredito

#FUNCIÓN ENCARGADA DE ASIGNAR EL NÚMERO DE COMPROBANTE
def asignarComprobante(mboMaterial):
    numComp = ""
    if mboMaterial.getString("ISSUETYPE") == "RETURN":
        numComp = 79
    elif mboMaterial.getString("ISSUETYPE") == "RECEIPT":
        itemSet = mxserver.getMboSet("ITEM", userinfo)
        itemSet.setWhere("ITEMNUM='"+mboMaterial.getString("ITEMNUM")+"'")
        if not itemSet.isEmpty():
            item = itemSet.moveFirst()
            if item.getBoolean("SLX_ESELECTRICO"):
                numComp = 71
            else:
                numComp = 41
    return numComp			

#FUNCIÓN QUE PERMITE VALIDAR EL ALMACÉN ENTRANTE QUE CORRESPONDA AL LEADER DE LA CUADRILLA (CONTROL DE CAMBIO)
def validarCuadrillaAlmacen(lineasMaterialesSet, lineasManoObraSet):
    respuestaValidacion = True
    if not(lineasMaterialesSet.isEmpty() or lineasManoObraSet.isEmpty()):
        material = lineasMaterialesSet.moveFirst()
        while material is not None:
            storeloc, siteid = material.getString("STORELOC"), material.getString("SITEID")
            locationsSet = mxserver.getMboSet("LOCATIONS", userinfo)
            locationsSet.setWhere("LOCATION='"+storeloc+"' AND SITEID='"+siteid+"'")
            if not locationsSet.isEmpty():
                locations = locationsSet.moveFirst()
                propietario = locations.getString("INVOWNER")
                logger.debug("*********************PROPIETARIO: "+propietario)
                manoObra = lineasManoObraSet.moveFirst()
                while manoObra is not None:
                    cuadrilla = manoObra.getString("AMCREW")
                    if cuadrilla != "":
                        amcrewSet = mxserver.getMboSet("AMCREW", userinfo)
                        amcrewSet.setWhere("AMCREW='"+cuadrilla+"'")
                        if not amcrewSet.isEmpty():
                            amcrew = amcrewSet.moveFirst()
                            amcrewlaborSet = amcrew.getMboSet("AMCREWLABOR")
                            amcrewlaborSet.setWhere("POSITION ='LEADER'")
                            if not amcrewlaborSet.isEmpty():
                                amcrewlabor = amcrewlaborSet.moveFirst()
                                laborcode = amcrewlabor.getString("LABORCODE")

                                if laborcode != propietario:
                                    return service.error("designer", "generic",[u"Líder no corresponde al propietario del almacén"])
                            else:
                                service.error("designer", "generic",[u"No existe líder asociado a la cuadrilla"])
                    else:
                        service.error("designer", "generic",[u"El valor para la cuadrilla es requerido"])
                    manoObra = lineasManoObraSet.moveNext()
            material = lineasMaterialesSet.moveNext()
    else:
        service.error("designer", "generic",[u"No existen Materiales y/o Mano de obra asociados"])
    return respuestaValidacion
	
#COMPROBANTES DESDE CONSUMO DE INVENTARIO
if launchPoint == "INVUSE" and status_modified and status == "COMPLETE":
    lineasConsumoInvSet = mbo.getMboSet("INVUSELINE")
    dictRespuestas = {}
    respuestaGuardar = False
	
    if not lineasConsumoInvSet.isEmpty():
        token = obtenerToken("")
        dictLineas = agruparItems(lineasConsumoInvSet, "INVUSE")
        
        for numComp, listaLineas in dictLineas.items():
            if len(listaLineas) > 0:
                logger.debug("*********************COMPROBANTE  NUMERO "+str(numComp)+" - INICIO")
                detalleComprobante = asignarLineas(listaLineas)
                codigoComprobante = "{\"intTipoComprobante\": "+str(numComp)+",\"lngNroComprobante\":\"\", \"fechaComprobante\":\""+fechaActual+"\",\"strConcepto\":\"DCTO: "+str(mbo.getString("INVUSENUM"))+"\",\"lisDetalles\": ["+detalleComprobante+"],\"lisDescuentos\": []}"
                logger.debug("*********************CODIGO COMPROBANTES: "+str(codigoComprobante.encode("utf-8")))
                responseStatus, response = invocarApi(URL_COMPROBANTES, codigoComprobante.encode("utf-8"), token)				
                
                if responseStatus < 400:
                    #COMPLETAR EN DICCIONARIO
                    lngNroComprobante = response
                    dictRespuestas[numComp] = (lngNroComprobante, fechaActual, listaLineas)
                    respuestaGuardar = True
                else:
                    respuestaGuardar = False
                    if anularComprobante(dictRespuestas, token, ""):
                        service.error("designer", "generic",[u"Error al enviar comprobante a SAF. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: "+response])
                logger.debug("*********************COMPROBANTE  NUMERO "+str(numComp)+" - FIN")

        if respuestaGuardar:
            guardarComprobante(dictRespuestas)
        	
#COMPROBANTES DESDE LA RECEPCIÓN MATERIALES(MATRECTRANS)
elif launchPoint == "MATRECTRANS" and status == "COMP" and (mbo.getString("ISSUETYPE") == "RECEIPT" or mbo.getString("ISSUETYPE") == "RETURN"):
    token = obtenerToken("")
    tipoComprobante = asignarComprobante(mbo)
    detalleComprobante = asignarLineasRecepcion(mbo)
    codigoComprobante = "{\"intTipoComprobante\": "+str(tipoComprobante)+",\"lngNroComprobante\":\"\", \"fechaComprobante\":\""+fechaActual+"\",\"strConcepto\":\"OC:"+mbo.getString("PONUM")+"/"+fechaActual+"/"+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\",\"lisDetalles\": ["+detalleComprobante+"],\"lisDescuentos\": []}"
    logger.debug("*********************CODIGO COMPROBANTES: "+str(codigoComprobante.encode("utf-8")))
    responseStatus, response = invocarApi(URL_COMPROBANTES, codigoComprobante.encode("utf-8"), token)
	
    if responseStatus < 400:
        mbo.setValue("SLXIDCOMPROBANTE", "COMP:"+str(tipoComprobante)+"/DCTO:"+response, 11L)
        logger.debug("*********************RESPUESTA GUARDADA")
    else:
        service.error("designer", "generic",[u"Error al enviar comprobante a SAF. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: "+response])

#COMPROBANTES DESDE LA RECEPCIÓN SERVICIOS (SERVRECTRANS)
elif launchPoint == "SERVRECTRANS" and status == "COMP" and (mbo.getString("ISSUETYPE") == "RECEIPT" or mbo.getString("ISSUETYPE") == "RETURN"):
    token = obtenerToken("")
    detalleComprobante = asignarLineasRecepcion(mbo)
    codigoComprobante = "{\"intTipoComprobante\": 51,\"lngNroComprobante\":\"\", \"fechaComprobante\":\""+fechaActual+"\",\"strConcepto\":\"OC:"+mbo.getString("PONUM")+"/"+fechaActual+"/"+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")+"\",\"lisDetalles\": ["+detalleComprobante+"],\"lisDescuentos\": []}"
    logger.debug("*********************CODIGO COMPROBANTES: "+str(codigoComprobante.encode("utf-8")))
    responseStatus, response = invocarApi(URL_COMPROBANTES, codigoComprobante.encode("utf-8"), token)
	
    if responseStatus < 400:
        mbo.setValue("SLXIDCOMPROBANTE", "COMP:51/DCTO:"+response, 11L)
        logger.debug("*********************RESPUESTA GUARDADA")
    else:
        service.error("designer", "generic",[u"Error al enviar comprobante a SAF. \nCódigo de Error: "+str(responseStatus)+". \nMensaje: "+response])
		
#COMPROBANTES DESDE ORDEN DE TRABAJO
elif launchPoint == "WORKORDER" and (status == "CERRADA" or status == "COMPLETA") and mbo.getString("EXTERNALREFID") != "" and mbo.getString("SOURCESYSID") == u"App Móvil" and not interactive:
    lineasMaterialesSet = mbo.getMboSet("MATUSETRANS")
    lineasManoObraSet = mbo.getMboSet("LABTRANS")
    dictRespuestas = {}
    respuestaGuardar = False
    if validarCuadrillaAlmacen(lineasMaterialesSet, lineasManoObraSet):
        token = obtenerToken("WORKORDER")
        dictLineas = agruparItems(lineasMaterialesSet, "WORKORDER")
        
        for numComp, listaLineas in dictLineas.items():
            if len(listaLineas) > 0:
                logger.debug("*********************COMPROBANTE  NUMERO "+str(numComp)+" - INICIO")
                detalleComprobante = asignarLineas(listaLineas)
                codigoComprobante = "{\"intTipoComprobante\": "+str(numComp)+",\"lngNroComprobante\":\"\", \"fechaComprobante\":\""+fechaActual+"\",\"strConcepto\":\"DCTO: "+str(mbo.getString("WONUM"))+"\",\"lisDetalles\": ["+detalleComprobante+"],\"lisDescuentos\": []}"
                logger.debug("*********************CODIGO COMPROBANTES: "+str(codigoComprobante.encode("utf-8")))
                responseStatus, response = invocarApi(URL_COMPROBANTES, codigoComprobante.encode("utf-8"), token)				
                
                if responseStatus < 400:
                    #COMPLETAR EN DICCIONARIO
                    lngNroComprobante = response
                    dictRespuestas[numComp] = (lngNroComprobante, fechaActual, listaLineas)
                    respuestaGuardar = True
                else:
                    respuestaGuardar = False
                    if anularComprobante(dictRespuestas, token, "WORKORDER"):
                        service.error("designer", "generic",[u""+response])
                logger.debug("*********************COMPROBANTE  NUMERO "+str(numComp)+" - FIN")

        if respuestaGuardar:
            guardarComprobante(dictRespuestas)
logger.debug("*********************FIN SLXINTEGRACIONSAFCOMP*********************")