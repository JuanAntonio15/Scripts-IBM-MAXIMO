#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 06-09-2021
#Descripción: Integración - Reemplazar el campo LOCATION por SLXLOCSPARD en la respuesta del ws de consulta de ubicaciones

from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************INICIO*********************")

mxserver = MXServer.getMXServer()
userinfo = mxserver.getSystemUserInfo()

if irData.getCurrentData("LOCATION") != None:
    locationsSet = mxserver.getMboSet("LOCATIONS", userinfo)
    locationsSet.setWhere("LOCATION='"+irData.getCurrentData("LOCATION")+"'")
    logger.debug("*********************LOCATIONSET: "+str(locationsSet.count()))

    if not locationsSet.isEmpty():
        location = locationsSet.moveFirst()
        logger.debug("*********************SLXLOCSPARD: "+str(location.getString("SLXLOCSPARD")))
        irData.setCurrentData("LOCATION", location.getString("SLXLOCSPARD"))

logger.debug("*********************FIN*********************")