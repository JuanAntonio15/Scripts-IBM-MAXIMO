#Autor: Juan Antonio González <juan.gonzalez@solex.cl>
#Fecha: 03-12-2019
#Descripción: Copiar valores de tabla SLXLECVARHIS a tablas hijas

from java.lang import System
from psdi.util.logging import MXLoggerFactory
from psdi.server import MXServer

logger = MXLoggerFactory.getLogger("maximo.script.customscript")
logger.debug("*********************PROCESARSLXLECTURAVAR: Inicio")

#Función: Recorrer Mbo y verificar cual id es no nulo para ingresar datos directamente en esa tabla detalle
def recorrerMbo(mbo):
    listaId = ["HA_IDAFORO","HAQ_IDANAQUIM","HCS_IDCUNA","HI_IDINFRA","HM_IDMEDESTACION","HNC_IDNVL","HNM_IDNVL","HQ_IDCOORDENADA","HSA_IDTAUXILIAR","HSL_IDSUPLAC","VT_IDVAR","WACP_ID","WAPD_ID","WC_ID","WPD_ID","WS_ID","WV_ID","WWE_ID"]
    idNoNulo = None
    for id in listaId:
        if not mbo.isNull(id) and mbo.getString(id) != "0" and mbo.getString(id) != "":
            idNoNulo = id
    return idNoNulo
		
#Variables
mxserver = MXServer.getMXServer()    
userinfo = mxserver.getSystemUserInfo()
inContador = 0

#Diccionario de de tablas y diccionario de atributos
diccionarioIdTabla = {"HA_IDAFORO":"SLXHA","HAQ_IDANAQUIM":"SLXHAQ","HCS_IDCUNA":"SLXHCS","HI_IDINFRA":"SLXHI","HM_IDMEDESTACION":"SLXHM","HNC_IDNVL":"SLXHNC","HNM_IDNVL":"SLXHNM","HQ_IDCOORDENADA":"SLXHQ","HSA_IDTAUXILIAR":"SLXHSA","HSL_IDSUPLAC":"SLXHSL","VT_IDVAR":"SLXVT","WACP_ID":"SLXWACP","WAPD_ID":"SLXWAPD","WC_ID":"SLXWC","WPD_ID":"SLXWPD","WS_ID":"SLXWS","WV_ID":"SLXWV","WWE_ID":"SLXWWE"}
diccionarioAtributos = {"HA_IDAFORO":{"HA_COMENTARIO":"string", "HA_ELIMINADO":"int", "HA_EMPRESA":"string","HA_FEC":"date", "HA_IDAFORO":"int", "HA_INFRA":"string", "HA_LOG":"int","HA_METODOFISICO":"string","HA_MODIFICADO":"int","HA_PUBLICADO":"int","HA_TIPOENSAYO":"string","HA_UNIDAD":"string","HA_VALIDADO":"int","HA_VALOR":"double"},"HAQ_IDANAQUIM":{"HAQ_ANALITO":"string","HAQ_COMENTARIO":"string","HAQ_DESCRIPTOR":"string","HAQ_ELIMINADO":"int","HAQ_FEC":"date","HAQ_IDANAQUIM":"int","HAQ_INFRA":"string","HAQ_LABORATORIO":"string","HAQ_LOG":"int","HAQ_MODIFICADO":"int","HAQ_PUBLICADO":"int","HAQ_UNIDAD":"string","HAQ_VALIDADO":"int","HAQ_VALOR":"double"},"HCS_IDCUNA":{"HCS_COMENTARIO":"string","HCS_ELIMINADO":"int","HCS_EMPRESA":"string","HCS_FEC":"date","HCS_IDCUNA":"int","HCS_INFRA":"string","HCS_LOG":"int","HCS_MODIFICADO":"int","HCS_PROFUNDIDAD":"float","HCS_PUBLICADO":"int","HCS_TIPOENSAYO":"string","HCS_UNIDAD":"string","HCS_VALIDADO":"int","HCS_VALOR":"double"},"HI_IDINFRA":{"HI_IDINFRA":"int","HI_NOMBREINFRA":"string","HI_POZOPC":"int","HI_PUBLICO":"int"},"HM_IDMEDESTACION":{"HM_COMENTARIO":"string","HM_ELIMINADO":"int","HM_ESTACION":"string","HM_FEC":"date","HM_FRECUENCIA":"string","HM_IDMEDESTACION":"int","HM_LOG":"int","HM_MODIFICADO":"int","HM_PARAMETRO":"string","HM_PUBLICADO":"int","HM_TIPODATO":"string","HM_UNIDAD":"string","HM_VALIDADO":"int","HM_VALOR":"double"},"HNC_IDNVL":{"HNC_COMENTARIO":"string","HNC_CTNVLMSNM":"double","HNC_CTPTOREFMSNM":"double","HNC_ELIMINADO":"int","HNC_EMPRESA":"string","HNC_FEC":"date","HNC_IDNVL":"int","HNC_INFRA":"string","HNC_LOG":"int","HNC_MEDBPTOREFM":"double","HNC_MODALIDADNVL":"string","HNC_MODIFICADO":"int","HNC_NBPRINICIAL":"double","HNC_NVLRELATIVO":"double","HNC_PLCONT":"int","HNC_PUBLICADO":"int","HNC_TIPONVL":"string","HNC_VALIDADO":"int"},"HNM_IDNVL":{"HNM_COMENTARIO":"string","HNM_CTNVLMSNM":"double","HNM_CTPTOREFMSNM":"double","HNM_ELIMINADO":"int","HNM_EMPRESA":"string","HNM_FEC":"date","HNM_IDNVL":"int","HNM_INFRA":"string","HNM_LOG":"int","HNM_MEDBPTOREFM":"double","HNM_MODALIDADNVL":"string","HNM_MODIFICADO":"int","HNM_NBPRINICIAL":"double","HNM_NVLRELATIVO":"double","HNM_PLCONT":"int","HNM_PUBLICADO":"int","HNM_TIPONVL":"string","HNM_VALIDADO":"int"},"HQ_IDCOORDENADA":{"HQ_CTPTOREFMSNM":"double","HQ_ELIMINADO":"int","HQ_FINVIG":"date","HQ_IDCOORDENADA":"int","HQ_INFRA":"string","HQ_INIVIG":"date","HQ_LOG":"int","HQ_UTMESTE":"double","HQ_UTMNORTE":"double"},"HSA_IDTAUXILIAR":{"HSA_CTFI":"double","HSA_CTFII":"double","HSA_DESCFI":"double","HSA_DESCFII":"double","HSA_ELIMINADO":"int","HSA_FECVIG":"date","HSA_GRAFINFERIOR":"double","HSA_GRAFSUPERIOR":"double","HSA_IDTAUXILIAR":"int","HSA_INFRA":"string","HSA_LOG":"int","HSA_SISTEMA":"string","HSA_SUBSISTEMA":"string"},"HSL_IDSUPLAC":{"HSL_COMENTARIO":"string","HSL_ELIMINADO":"int","HSL_EMPRESA":"string","HSL_FEC":"date","HSL_IDSUPLAC":"int","HSL_INFRA":"string","HSL_LOG":"int","HSL_MODIFICADO":"int","HSL_PUBLICADO":"int","HSL_TIPOENSAYO":"string","HSL_TIPOMETODO":"string","HSL_UNIDAD":"string","HSL_VALIDADO":"int","HSL_VALOR":"double"},"VT_IDVAR":{"VT_DESC":"string","VT_FEC":"date","VT_IDVAR":"string","VT_RESULTNUMBER":"double","VT_SVALOR":"string","VT_VALOR":"double"},"VV_IDVAR":{"VV_A":"string","VV_DESC":"string","VV_DESCVAR":"string","VV_IDVAR":"string"},"WACP_ID":{"WACP_CLTNID":"int","WACP_CREATEDAT":"date","WACP_DESCID":"int","WACP_DESTID":"int","WACP_EXTRIGHTS":"int","WACP_ID":"int","WACP_ISENABLED":"int","WACP_LABEL":"string","WACP_LAT":"string","WACP_LNG":"string","WACP_LOCATIONID":"int","WACP_NAME":"string","WACP_PUMPID":"int","WACP_SECTORID":"int","WACP_TYPEID":"int","WACP_UPDATEDAT":"date"},"WAPD_ID":{"WAPD_AMBCTRLPTID":"int","WAPD_CREATEDAT":"date","WAPD_ID":"int","WAPD_PLTORPLEXT":"double","WAPD_SECTORID":"int","WAPD_TIMESTAMP":"date","WAPD_UPDATEDAT":"date"},"WC_ID":{"WC_BRDENSITY":"double","WC_CREATEDAT":"date","WC_F1":"double","WC_F2":"double","WC_IBAMOP":"double","WC_IBASOP":"double","WC_ID":"int","WC_ISENABLED":"int","WC_LITERSPERSEC":"double","WC_SALTDENSITY":"double","WC_UPDATEDAT":"date"},"WPD_ID":{"WPD_BRDPS":"double","WPD_CONSTANTID":"int","WPD_CREATEDAT":"date","WPD_EVNAIMPRDPS":"double","WPD_EVNBRIMPRDPS":"double","WPD_EVNEXPADPS":"double","WPD_EVNEXPBRDPS":"double","WPD_EVNSTKCI":"double","WPD_ID":"int","WPD_IMPRBRADPS":"double","WPD_INDIRREINJ":"double","WPD_ISOF":"int","WPD_ISOFDATUM":"int","WPD_ISPROCESSING":"int","WPD_LAGOONA":"double","WPD_NETEXTLS":"double","WPD_NETEXTMD":"double","WPD_PCTSLPULPDPS":"double","WPD_PLEXT":"double","WPD_PLTEXT":"double","WPD_PULPFLOWDPS":"double","WPD_RECYCLEBRDPS":"double","WPD_SECTORID":"int","WPD_TIMESTAMP":"date","WPD_TOTALEXT":"double","WPD_UPDATEDAT":"date"},"WS_ID":{"WS_CREATEDAT":"date","WS_ID":"int","WS_NAME":"string","WS_UPDATEDAT":"date"},"WV_ID":{"WV_COMMENT":"string","WV_CREATEDAT":"date","WV_EVENT":"string","WV_ID":"int","WV_ITEMID":"int","WV_ITEMTYPE":"string","WV_OBJECT":"string","WV_WHODUNNIT":"string"},"WWE_ID":{"WWE_AMBCTRLPTID":"int","WWE_AVGFLOWDAY":"float","WWE_CREATEDAT":"date","WWE_FLOWDAY":"float","WWE_ID":"int","WWE_ISPROCESSING":"int","WWE_TIMESTAMP":"date","WWE_UPDATEDAT":"date"}}

mboSetLecturaVariables = mxserver.getMboSet("SLXLECVARHIS", userinfo)
mboSetLecturaVariables.setWhere("STATUS = 'INGRESADO'")
mboSetLecturaVariables.setOrderBy("SLXLECTURAVARID ASC")
mboSetLecturaVariables.setDBFetchMaxRows(2000)
logger.debug("*********************PROCESARSLXLECTURAVAR: Esta vacio el mboSet de Lectura de Variables?: "+str(mboSetLecturaVariables.isEmpty()))

#Validar si tiene registros por procesar
if(mboSetLecturaVariables.isEmpty() is False):

    #Recorrido de registros en la tabla SLXLECVARHIS
    mboLecturaVariables = mboSetLecturaVariables.moveFirst()
    while(mboLecturaVariables is not None and inContador < 2000):
	
		#id no nulo
        idTablanoNulo = recorrerMbo(mboLecturaVariables)
        logger.debug("*********************PROCESARSLXLECTURAVAR: idTablanoNulo : "+str(idTablanoNulo))
		
        if idTablanoNulo is not None:
		    #Tabla dinámica obtenida por el id que no es nulo del correspondiente diccionario
            mboSetSLXTABLA = mxserver.getMboSet(diccionarioIdTabla.get(idTablanoNulo), userinfo)
            mboSetSLXTABLA.setWhere("1=0")
            logger.debug("*********************PROCESARSLXLECTURAVAR: Esta vacia la tabla dinamica? (Debe ser siempre True) : "+str(mboSetSLXTABLA.isEmpty()))
            mboTabla = mboSetSLXTABLA.add(11L)

            #Atributos que siempre llevarán valor
            mboTabla.setValue("SLXLECTURAVARID", mboLecturaVariables.getInt("SLXLECTURAVARID"), 11L)
            mboTabla.setValue("REMARKS", mboLecturaVariables.getString("REMARKS"), 11L)
            mboTabla.setValue("STATUS","PROCESADO", 11L)
            mboTabla.setValue("TRANSDATE",mboLecturaVariables.getDate("TRANSDATE"), 11L)
				
            #Recorrer diccionario de id no nulo. Copiar los valores
            for atributo, tipoDato in diccionarioAtributos.get(idTablanoNulo).items():             
                if mboLecturaVariables.isNull(atributo):
                    mboTabla.setValueNull(atributo, 11L)
                else:
                    if tipoDato == "string":
                        mboTabla.setValue(atributo, mboLecturaVariables.getString(atributo), 11L)
                    elif tipoDato == "int":
                        mboTabla.setValue(atributo, mboLecturaVariables.getInt(atributo), 11L)
                    elif tipoDato == "double":
                        mboTabla.setValue(atributo, mboLecturaVariables.getDouble(atributo), 11L)
                    elif tipoDato == "float":
                        mboTabla.setValue(atributo, mboLecturaVariables.getFloat(atributo), 11L)
                    elif tipoDato == "date":
                        mboTabla.setValue(atributo, mboLecturaVariables.getDate(atributo), 11L)
        
		    #Save
            mboSetSLXTABLA.save()
            logger.debug("*********************PROCESARSLXLECTURAVAR: Save en tabla detalle de SLXLECTURAVARID:"+str(mboLecturaVariables.getString("SLXLECTURAVARID")))		
            
        #CAMBIAR ESTADO A REGISTRO QUE FUE PROCESADO                     
        mboLecturaVariables.setValue("STATUS","PROCESADO",11L)		
        inContador = inContador + 1
        logger.debug("*********************PROCESARSLXLECTURAVAR: Cambio de estado de registro en SLXLECVARHIS")
        
        #SIGUIENTE REGISTRO
        mboLecturaVariables = mboSetLecturaVariables.moveNext()
        
    #SAVE DEL REGISTRO DE LECTURA
    mboSetLecturaVariables.save()
       
#CIERRE SET LECTURA VARIABLES
mboSetLecturaVariables.close()
logger.debug("*********************PROCESARSLXLECTURAVAR: Fin")