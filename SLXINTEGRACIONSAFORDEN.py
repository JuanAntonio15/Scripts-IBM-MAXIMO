#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 08-11-2021
#Descripción: Integración con el sistema externo SAF para orden de pago

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer
from java.util import HashMap, Date
from psdi.iface.router import HTTPHandler
from java.text import SimpleDateFormat
from com.ibm.json.java import JSONObject

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO SLXINTEGRACIONSAFORDENPAGO*********************")
mxserver = MXServer.getMXServer()
userinfo = mxserver.getSystemUserInfo()
fechaActual = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").format(Date())

#URL
URL_LOGIN = "https://172.25.2.39:15024/api/autenticacion/login"
URL_ORDENPAGO = "https://172.25.2.39:15024/api/OrdenPago"

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

#FUNCIÓN ENCARADA DE OBTENER LA INFORMACIÓN DE LA PO RELACIONADA	
def obtenerInfoPO(ponum, siteid):
    slxtipodoc2 = slxrpr = ""
    poSet = mxserver.getMboSet("PO", userinfo)
    poSet.setWhere("SITEID='"+siteid+"' AND PONUM='"+ponum+"'")
    if not poSet.isEmpty():
        po = poSet.moveFirst()
        slxtipodoc2 = po.getString("SLXTIPODOC2")
        slxrpr = po.getString("SLXRPR")
    return slxtipodoc2, slxrpr
	
#FUNCIÓN ENCARGADA DE RECORRER LAS LÍNEAS DE INVOICELINE
def asignarLineasINV(invoiceLineSet):
    logger.debug("*******************FUNC ASIGNAR LINEAS - INICIO")
    codigoLineas, area, vigencia, proyecto, cuentaCredito = "", "", "", "", ""
    invoiceline = invoiceLineSet.moveFirst()
    indice = 1

    while(invoiceline is not None):
        invoicecost = (invoiceline.getMboSet("INVOICECOST")).moveFirst()
        cuentaCredito = invoicecost.getString("GLCREDITACCT")
        area, vigencia, proyecto = obtenerInfoProyecto(invoicecost)
        cuentaContable = obtenerInfoEmpresa(invoicecost)
        centroCosto = (invoicecost.getString("GLDEBITACCT")).split("-")[0]
        tax = invoiceline.getInt("TAX1") if invoiceline.getInt("TAX1") > 0 else invoiceline.getInt("TAX2")
        decPorcIva = (tax*100)/invoiceline.getInt("LINECOST")
        strContabilizaIva = "N" if invoiceline.getDouble("TAX1FORUI") > 0 else "S"
        if indice < invoiceLineSet.count():
            codigoLineas = codigoLineas + "{\"intRengln\": "+str(indice)+", \"strCuentaPpto\": \""+str(invoicecost.getString("FCTASKID"))+"\", \"strCodigoArea\": \""+area+"\", \"strCodigoProyecto\": \""+proyecto+"\", \"strCentroCosto\": \"5109999\", \"strCuentaContable\": \""+cuentaContable+"\", \"decValorSinIva\": "+str(invoiceline.getInt("LINECOST"))+", \"decPorcIva\": "+str(decPorcIva)+", \"strContabilizaIva\": \""+str(strContabilizaIva)+"\"},"
        else:
            codigoLineas = codigoLineas + "{\"intRengln\": "+str(indice)+", \"strCuentaPpto\": \""+str(invoicecost.getString("FCTASKID"))+"\", \"strCodigoArea\": \""+area+"\", \"strCodigoProyecto\": \""+proyecto+"\", \"strCentroCosto\": \"5109999\", \"strCuentaContable\": \""+cuentaContable+"\", \"decValorSinIva\": "+str(invoiceline.getInt("LINECOST"))+", \"decPorcIva\": "+str(decPorcIva)+", \"strContabilizaIva\": \""+str(strContabilizaIva)+"\"}"
        indice += 1
        invoiceline = invoiceLineSet.moveNext()
    logger.debug("*******************FUNC ASIGNAR LINEAS - FIN")
    return codigoLineas, vigencia, cuentaCredito

#FUNCIÓN QUE PERMITE OBTENER INFORMACIÓN DEL PROYECTO
def obtenerInfoProyecto(invoicecost):
    area = ""
    vigencia = ""
    proyecto = ""
    proyectoMboSet = mxserver.getMboSet("FINCNTRL", userinfo)
    proyectoMboSet.setWhere("FINCNTRLID='"+invoicecost.getString("FINCNTRLID")+"'")
    proyectoMbo = proyectoMboSet.moveFirst()
    fincntrlSet = mxserver.getMboSet("FINCNTRL", userinfo)
    fincntrlSet.setWhere("PROJECTID='"+proyectoMbo.getString("PROJECTID")+"' AND SLXAR IS NOT NULL AND SLXVI IS NOT NULL AND SLXPR IS NOT NULL")
    if not fincntrlSet.isEmpty():
        fincntrl = fincntrlSet.moveFirst()
        area = fincntrl.getString("SLXAR")
        vigencia = fincntrl.getInt("SLXVI")
        proyecto = fincntrl.getString("SLXPR")
    logger.debug("*******************FUNC INFO PROYECTO - FIN")		
    return area, vigencia, proyecto
	
#FUNCIÓN QUE PERMITE OBTENER INFORMACIÓN DE LA EMPRESA
def obtenerInfoEmpresa(invoicecost):
    apsuspenseacc = ""
    companiesSet = mxserver.getMboSet("COMPANIES", userinfo)
    companiesSet.setWhere("COMPANY='"+invoicecost.getString("VENDOR")+"'")
    if not companiesSet.isEmpty():
        company = companiesSet.moveFirst()
        apsuspenseacc = company.getString("APSUSPENSEACC")
    return apsuspenseacc.split("-")[0]
	
#ORDEN DE PAGO DE LA FACTURA (INVOICE)
if launchPoint == "INVOICE":
    logger.debug("*********************FACTURA - INICIO")
    invoiceLineSet = mbo.getMboSet("INVOICELINE")
    if status_modified and status == "PAID" and invoiceLineSet.isEmpty() is False:
        token = obtenerToken()
        fechaActual = SimpleDateFormat("yyyy-MM-dd").format(Date())
        fechaFactura = SimpleDateFormat("yyyy-MM-dd").format(mbo.getDate("INVOICEDATE")) if not mbo.isNull("INVOICEDATE") else ""
        fechaRadicado = SimpleDateFormat("yyyy-MM-dd").format(mbo.getDate("SLXFECHARAD")) if not mbo.isNull("SLXFECHARAD") else ""
        slxtipodoc2, slxrpr = obtenerInfoPO(mbo.getString("PONUM"), mbo.getString("SITEID"))
        lineasINV, vigencia, cuentaCredito = asignarLineasINV(invoiceLineSet)
        desc = "FACTURA:"+mbo.getString("INVOICENUM")+"/PLANTA:"+mbo.getString("SITEID")+"/"+(mbo.getString("DESCRIPTION")).replace("\"","\\\"")
        codigoINV = "{\"strTipoDocumento\": \""+slxtipodoc2+"\", \"strNroDocumento\": \""+slxrpr+"\", \"intVigenciaDocumento\": \""+str(vigencia)+"\", \"datFechaTransaccion\":\""+fechaActual+"\", \"strDescripcion\": \""+desc+"\", \"datFechaFactura\": \""+fechaFactura+"\",\"strNroFactura\": \""+mbo.getString("VENDORINVOICENUM")+"\", \"strNroRadicado\": \""+str(mbo.getInt("SLXRADICADO"))+"\", \"datFechaRadicacion\": \""+fechaRadicado+"\", \"intDiasPlazo\": \"\", \"strConceptoRetencion\": \""+mbo.getString("SLXRETENCION")+"\", \"strCuentaPasivo\": \"\", \"lisDetalles\": ["+lineasINV+"]}"
        logger.debug("*******************CODIGO INVOICE: "+str(codigoINV.encode("utf-8")))				
        responseStatus, responseStatusText, response = invocarApi(URL_ORDENPAGO, codigoINV.encode("utf-8"), token)
        ordenPagoJSON = JSONObject.parse(response)
        mbo.setValue("SLXIDCOMPROBANTE", "OP:"+str(ordenPagoJSON.get("intOrdenPago"))+"/TC:"+str(ordenPagoJSON.get("intTipoComprobante"))+"/NC:"+str(ordenPagoJSON.get("lngNroComprobante")), 11L)
    logger.debug("*********************FACTURA - FIN")
logger.debug("*********************FIN SLXINTEGRACIONSAFORDENPAGO*********************")