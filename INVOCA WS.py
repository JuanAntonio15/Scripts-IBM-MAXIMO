#Autor: Juan Antonio González <juan.gonzalez@solex.biz>
#Fecha: 05-02-2021
#Descripción: Gatillar invocación de WS de Integración con Aplicación Móvil

from psdi.iface.mic import InvokeChannelCache
from psdi.iface.mic import PublishChannelCache
from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer

mxserver = MXServer.getMXServer()
userInfo = mxserver.getSystemUserInfo()
logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************Inicio: Script Invoca WS de Integracion")
  
if launchPoint == "WOSAVE":
    wonum = mbo.getString("WONUM")
    slxmovilidad = mbo.getInt("SLXMOVILIDAD")
	
    logger.debug("********************* status: "+str(status))
    logger.debug("********************* wonum: "+str(wonum))
    logger.debug("********************* slxmovilidad: "+str(slxmovilidad))
    logger.debug("********************* Se modifica el estado?: "+str(status_modified))
	
    if(slxmovilidad == 1 and status_modified and status == 'APPR' and interactive):       
        InvokeChannelCache.getInstance().getInvokeChannel("CrearOTAPP").invoke(None, mbo, mbo, None)
              
logger.debug("*********************Fin: Script Invoca WS de Integracion")