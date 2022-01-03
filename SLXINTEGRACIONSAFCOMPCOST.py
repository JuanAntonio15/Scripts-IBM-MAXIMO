#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 15-11-2021
#Descripción: Integración con el sistema externo SAF para comprobantes

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer
from java.util import HashMap, Date
from psdi.iface.router import HTTPHandler
from java.text import SimpleDateFormat

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO SLXINTEGRACIONSAFCOMP*********************")
mxserver = MXServer.getMXServer()
userinfo = mxserver.getSystemUserInfo()

#URL
URL_LOGIN = "https://172.25.2.39:15024/api/autenticacion/login"
URL_COMPROBANTES = "https://172.25.2.39:15024/api/Comprobantes"

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
    token = ""
    codigoLogin = "{\"strUsuario\": \"SAFWS_CNX\",\"strPassword\": \"desar\",\"strDominioLdap\": \"B_EEP\"}"
    responseStatus, responseStatusText, response = invocarApi(URL_LOGIN, codigoLogin, None)
    token = response[1:len(response) - 1]
    logger.debug("*********************FUNC. OBTENER TOKEN - FIN")
    return token

#FUNCIÓN ENCARGADA DE DIVIDIR LA LÍNEA DE CRÉDITO Y DÉBITO REQUERIDO POR SAF
def crearCodigoJSON(primerCuenta, segundaCuenta, descripcion, decValorMovimientoD, decValorMovimientoC):
    fechaActual = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(Date())
    cuentaContableD, centroCostoD = asignarCuentas(primerCuenta.split("-"))
    cuentaContableC, centroCostoC = asignarCuentas(segundaCuenta.split("-"))
    detalleComprobante = "{\"intNroRenglon\": 1,\"strCuentaContable\":\""+cuentaContableD+"\",\"lngNit\":\"1\",\"strClaseMovimiento\": \"D\",\"decValorMovimiento\": "+str(decValorMovimientoD)+",\"strDescripcion\": \""+descripcion+"\", \"strCentroCosto\":\""+centroCostoD+"\"}, {\"intNroRenglon\": 2,\"strCuentaContable\":\""+cuentaContableC+"\",\"lngNit\":\"1\",\"strClaseMovimiento\": \"C\",\"decValorMovimiento\": "+str(decValorMovimientoC)+",\"strDescripcion\": \""+descripcion+"\", \"strCentroCosto\":\""+centroCostoC+"\"}"
    codigoComprobante = "{\"intTipoComprobante\": 49,\"lngNroComprobante\":\"\", \"fechaComprobante\":\""+fechaActual+"\",\"strConcepto\":\"\",\"lisDetalles\": ["+detalleComprobante+"],\"lisDescuentos\": []}"
    return codigoComprobante

#FUNCIÓN QUE PERMITE ASIGNAR CUENTAS POR SEGMENTO, SI NO TIENE VALOR QUEDA NONE
def asignarCuentas(cuenta):
    cuentaPos0 = cuentaPos1 = ""
    if(len(cuenta) == 1):
        cuentaPos0 = cuenta[0]
    elif(len(cuenta) == 2):
        cuentaPos0 = cuenta[0]
        cuentaPos1 = cuenta[1]
    return cuentaPos0, cuentaPos1

#COMPROBANTES DESDE AJUSTES DE INVENTARIO
if launchPoint == "INVTRANS" and mbo.getString("TRANSTYPE") in("AVGCSTADJ", "RECBALADJ", "CURBALADJ"):
    codigoComprobante = ""
    descripcion = ""
	
    #1.1.- 	AJUSTE DE INVENTARIO DE COSTO PROMEDIO
    if mbo.getString("TRANSTYPE") == "AVGCSTADJ":
        descripcion = "Ajuste de Inventario de Costo Promedio"
			
    #1.2.- 	ACCIÓN CONCILIAR BALANCE
    elif mbo.getString("TRANSTYPE") == "RECBALADJ":
        descripcion = "Ajuste Conciliar Balance"
			
    #1.3.- 	ACCIÓN BALANCE ACTUAL
    elif mbo.getString("TRANSTYPE") == "CURBALADJ":
        descripcion = "Ajuste Balance Actual"
        
    linecost = mbo.getDouble("LINECOST")
    if linecost > 0:
        codigoComprobante = crearCodigoJSON(mbo.getString("GLDEBITACCT"), mbo.getString("GLCREDITACCT"), descripcion, linecost, linecost*-1)
    elif linecost < 0:
        codigoComprobante = crearCodigoJSON(mbo.getString("GLCREDITACCT"), mbo.getString("GLDEBITACCT"), descripcion, linecost*-1, linecost)
    else:
        service.error("designer", "generic",[u"Error \n Línea de costo no puede tener valor cero (0)"])
		
    logger.debug("*********************COMPROBANTE  NUMERO 49 - INICIO")
    token = obtenerToken()
    logger.debug("*********************CODIGO COMPROBANTES: "+str(codigoComprobante.encode("utf-8")))
    responseStatus, responseStatusText, response = invocarApi(URL_COMPROBANTES, codigoComprobante.encode("utf-8"), token)
    mbo.setValue("SLXIDCOMPROBANTE", "COMP:49/DCTO:"+response, 11L)
    logger.debug("*********************COMPROBANTE  NUMERO 49 - FIN")
logger.debug("*********************FIN SLXINTEGRACIONSAFCOMP*********************")