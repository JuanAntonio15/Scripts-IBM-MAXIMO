#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 25-11-2020
#Descripción: Invocación de integración de salida con MAXIMO-IDEA

from psdi.iface.mic import PublishChannelCache
from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer

mxserver = MXServer.getMXServer() 
userInfo = mxserver.getSystemUserInfo()
logger = MXLoggerFactory.getLogger("maximo.script.customscript")

logger.debug("*********************Inicio: Script Integracion MAXIMO-IDEA")
logger.debug("********************* wonum: "+str(mbo.getString("WONUM")))
logger.debug("********************* status: "+str(status))
logger.debug("********************* status_modified: "+str(status_modified))
logger.debug("********************* interactive: "+str(interactive))

if status_modified and status == 'ESPPROG' and interactive:
    #Obtener Materiales
    materialMboSet = mbo.getMboSet("SHOWALLPLANMATERIAL")
    logger.debug("********************* Materiales: "+str(materialMboSet.count()))

    #Obtener Servicios
    servicioMboSet = mbo.getMboSet("SHOWALLPLANSERVICE")
    logger.debug("********************* Servicios: "+str(servicioMboSet.count()))

    #Integración de salida para reserva de servicios
    if servicioMboSet.count() > 0:
        logger.debug("********************* Reserva de Servicios")
        PublishChannelCache.getInstance().getPublishChannel("ReservaServIDEA").publish(mbo, True)

    #Integración de salida para reserva de materiales
    if materialMboSet.count() > 0:
        logger.debug("********************* Reserva de Materiales")
        PublishChannelCache.getInstance().getPublishChannel("ReservaMatIDEA").publish(mbo, True)

logger.debug("*********************Fin: Script Integracion MAXIMO-IDEA")