from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TickerPreset(BaseModel):
    symbol: str
    name: str


# TA-125 index constituents (TASE's 125 largest/most liquid companies),
# resolved from company name to Yahoo Finance ticker and each verified with
# a real live price -- see scripts/resolve_ta125_tickers.py,
# scripts/resolve_ta125_retry.py and scripts/resolve_ta125_guess.py. 119 of
# the 125 names resolved; the other 6 (Phoenix Holdings, Paz Oil, GavYam
# Lands, Keystone Reit, Econergy Renewable Energy, and More Investment
# House) couldn't be confidently matched to a Yahoo Finance TASE listing and
# were left out rather than guessed. Re-run those scripts to refresh this
# list if the TA-125 composition changes.
TICKER_PRESETS: list[TickerPreset] = [
    TickerPreset(symbol="AFPR.TA", name="AFI Properties"),
    TickerPreset(symbol="ARGO.TA", name="ARGO Properties N.V."),
    TickerPreset(symbol="ACKR.TA", name="Ackerstein Group"),
    TickerPreset(symbol="AFRE.TA", name="Africa Israel Residences"),
    TickerPreset(symbol="ARPT.TA", name="Airport City"),
    TickerPreset(symbol="ALHE.TA", name="Alony-Hetz Properties & Investments"),
    TickerPreset(symbol="AMOT.TA", name="Amot Investments"),
    TickerPreset(symbol="AMPA.TA", name="Ampa"),
    TickerPreset(symbol="AMRM.TA", name="Amram Avraham Construction Company"),
    TickerPreset(symbol="ARYT.TA", name="Aryt Industries"),
    TickerPreset(symbol="ASHG.TA", name="Ashtrom Group"),
    TickerPreset(symbol="AURA.TA", name="Aura Investments"),
    TickerPreset(symbol="AYAL.TA", name="Ayalon Insurance Company"),
    TickerPreset(symbol="AZRM.TA", name="Azorim-Investment, Development & Construction Co."),
    TickerPreset(symbol="AZRG.TA", name="Azrieli Group"),
    TickerPreset(symbol="BIG.TA", name="BIG Shopping Centers"),
    TickerPreset(symbol="POLI.TA", name="Bank Hapoalim B.M."),
    TickerPreset(symbol="LUMI.TA", name="Bank Leumi le-Israel B.M."),
    TickerPreset(symbol="BSEN.TA", name="Bet Shemesh Engines Holdings (1997)"),
    TickerPreset(symbol="BEZQ.TA", name="Bezeq The Israel Telecommunication Corp."),
    TickerPreset(symbol="BLSR.TA", name="Blue Square Real Estate"),
    TickerPreset(symbol="CAMT.TA", name="Camtek"),
    TickerPreset(symbol="CRSM.TA", name="Carasso Motors"),
    TickerPreset(symbol="CEL.TA", name="Cellcom Israel"),
    TickerPreset(symbol="CLIS.TA", name="Clal Insurance Enterprises Holdings"),
    TickerPreset(symbol="DANE.TA", name="Danel (Adir Yeoshua)"),
    TickerPreset(symbol="DNYA.TA", name="Danya Cebus"),
    TickerPreset(symbol="DLEKG.TA", name="Delek Group"),
    TickerPreset(symbol="DELG.TA", name="Delta Galil Industries"),
    TickerPreset(symbol="DLTI.TA", name="Delta Israel Brands"),
    TickerPreset(symbol="DORL.TA", name="Doral Group Renewable Energy Resources"),
    TickerPreset(symbol="ELAL.TA", name="El Al Israel Airlines"),
    TickerPreset(symbol="ESLT.TA", name="Elbit Systems"),
    TickerPreset(symbol="ELCO.TA", name="Elco"),
    TickerPreset(symbol="ELTR.TA", name="Electra"),
    TickerPreset(symbol="ELCRE.TA", name="Electra Real Estate"),
    TickerPreset(symbol="ENOG.TA", name="Energean"),
    TickerPreset(symbol="ENRG.TA", name="Energix - Renewable Energies"),
    TickerPreset(symbol="ENLT.TA", name="Enlight Renewable Energy"),
    TickerPreset(symbol="EQTL.TA", name="Equital"),
    TickerPreset(symbol="FIBIH.TA", name="F.I.B.I. Holdings"),
    TickerPreset(symbol="FTAL.TA", name="Fattal Holdings (1998)"),
    TickerPreset(symbol="FIBI.TA", name="First International Bank of Israel"),
    TickerPreset(symbol="FORTY.TA", name="Formula Systems (1985)"),
    TickerPreset(symbol="FOX.TA", name="Fox-Wizel"),
    TickerPreset(symbol="GNRS.TA", name="Generation Capital"),
    TickerPreset(symbol="GLTL.TA", name="Gilat Telecom Global"),
    TickerPreset(symbol="HARL.TA", name="Harel Insurance Investments & Financial Services"),
    TickerPreset(symbol="HLAN.TA", name="Hilan"),
    TickerPreset(symbol="IBI.TA", name="I.B.I. Investment House"),
    TickerPreset(symbol="IDIN.TA", name="I.D.I. Insurance Company"),
    TickerPreset(symbol="IES.TA", name="I.E.S Holdings"),
    TickerPreset(symbol="ICL.TA", name="ICL Group"),
    TickerPreset(symbol="INRM.TA", name="Inrom Construction Industries"),
    TickerPreset(symbol="ISCD.TA", name="Isracard"),
    TickerPreset(symbol="ICHO.TA", name="Israel Canada Hotels"),
    TickerPreset(symbol="ILCO.TA", name="Israel Corporation"),
    TickerPreset(symbol="DSCT.TA", name="Israel Discount Bank"),
    TickerPreset(symbol="ISHI.TA", name="Israel Shipyards Industries"),
    TickerPreset(symbol="ISRA.TA", name="Isramco Negev 2 Limited Partnership"),
    TickerPreset(symbol="ISHO.TA", name="Isras Holdings"),
    TickerPreset(symbol="ISRO.TA", name="Isrotel"),
    TickerPreset(symbol="KEN.TA", name="Kenon Holdings"),
    TickerPreset(symbol="ACRO.TA", name="Kvutzat Acro"),
    TickerPreset(symbol="LAHAV.TA", name="Lahav LR Real Estate"),
    TickerPreset(symbol="LPHL.TA", name="Lapidoth-Heletz Limited Partnership"),
    TickerPreset(symbol="YHNF.TA", name="M.Yochananof and Sons (1988)"),
    TickerPreset(symbol="MTRX.TA", name="Matrix IT"),
    TickerPreset(symbol="MAXO.TA", name="Max Stock"),
    TickerPreset(symbol="MGOR.TA", name="Mega Or Holdings"),
    TickerPreset(symbol="MTAV.TA", name="Meitav Investment House"),
    TickerPreset(symbol="MLSR.TA", name="Melisron"),
    TickerPreset(symbol="MMHD.TA", name="Menora Mivtachim Holdings"),
    TickerPreset(symbol="MSKE.TA", name="Meshek Energy - Renewable Energies"),
    TickerPreset(symbol="MGDL.TA", name="Migdal Insurance and Financial Holdings"),
    TickerPreset(symbol="MVNE.TA", name="Mivne Real Estate (K.D)"),
    TickerPreset(symbol="MISH.TA", name="Mivtach Shamir Holdings"),
    TickerPreset(symbol="MZTF.TA", name="Mizrahi Tefahot Bank"),
    TickerPreset(symbol="NICE.TA", name="NICE"),
    TickerPreset(symbol="NVPT.TA", name="Navitas Petroleum, Limited Partnership"),
    TickerPreset(symbol="NYAX.TA", name="Nayax"),
    TickerPreset(symbol="NTML.TA", name="Neto Malinda Trading"),
    TickerPreset(symbol="NWMD.TA", name="NewMed Energy - Limited Partnership"),
    TickerPreset(symbol="NXSN.TA", name="NextVision Stabilized Systems"),
    TickerPreset(symbol="NVMI.TA", name="Nova"),
    TickerPreset(symbol="NOFR.TA", name="O.Y. Nofar Energy"),
    TickerPreset(symbol="OPCE.TA", name="OPC Energy"),
    TickerPreset(symbol="OPK.TA", name="OPKO Health"),
    TickerPreset(symbol="ORL.TA", name="Oil Refineries"),
    TickerPreset(symbol="ONE.TA", name="One Software Technologies"),
    TickerPreset(symbol="ORA.TA", name="Ormat Technologies"),
    TickerPreset(symbol="PTNR.TA", name="Partner Communications Company"),
    TickerPreset(symbol="PRSK.TA", name="Prashkovsky Investments and Construction"),
    TickerPreset(symbol="PRTC.TA", name="Priortech"),
    TickerPreset(symbol="PTBL.TA", name="Property & Building Corp."),
    TickerPreset(symbol="QLTU.TA", name="Qualitau"),
    TickerPreset(symbol="RPOL.TA", name="RP Optical Lab"),
    TickerPreset(symbol="RMLI.TA", name="Rami Levi Chain Stores Hashikma Marketing 2006"),
    TickerPreset(symbol="RATI.TA", name="Ratio Energies - Limited Partnership"),
    TickerPreset(symbol="RIT1.TA", name="Reit 1"),
    TickerPreset(symbol="RMON.TA", name="Rimon Consulting & Management Services"),
    TickerPreset(symbol="SCOP.TA", name="Scope Metals Group"),
    TickerPreset(symbol="SLARL.TA", name="Sella Capital Real Estate"),
    TickerPreset(symbol="SPEN.TA", name="Shapir Engineering and Industry"),
    TickerPreset(symbol="SBEN.TA", name="Shikun & Binui Energy"),
    TickerPreset(symbol="SKBN.TA", name="Shikun & Binui"),
    TickerPreset(symbol="SAE.TA", name="Shufersal"),
    TickerPreset(symbol="STRS.TA", name="Strauss Group"),
    TickerPreset(symbol="SMT.TA", name="Summit Real Estate Holdings"),
    TickerPreset(symbol="TMRP.TA", name="Tamar Petroleum"),
    TickerPreset(symbol="TEVA.TA", name="Teva Pharmaceutical Industries"),
    TickerPreset(symbol="TASE.TA", name="The Tel-Aviv Stock Exchange"),
    TickerPreset(symbol="TSEM.TA", name="Tower Semiconductor"),
    TickerPreset(symbol="TRPZ.TA", name="Turpaz Industries"),
    TickerPreset(symbol="UNMI.TA", name="Universal Motors Israel"),
    TickerPreset(symbol="VRDS.TA", name="Veridis Environment"),
    TickerPreset(symbol="VILR.TA", name="Villar International"),
    TickerPreset(symbol="WESR.TA", name="Wesure Global Tech"),
    TickerPreset(symbol="DIMRI.TA", name="Y.H. Dimri Construction & Development"),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_from_email: str = ""
    alert_to_email: str = ""

    poll_interval_seconds: int = 45
    default_threshold_pct: float = 2.0

    db_path: str = "./data/app.db"


settings = Settings()
