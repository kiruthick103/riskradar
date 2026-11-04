from typing import Dict, Any, List
from pydantic import BaseModel

class TenantConfig(BaseModel):
    tenant_id: str
    company_name: str
    display_title: str
    primary_color: str
    accent_color: str
    life_saving_rules: List[str]
    scoring_weights: Dict[str, float]
    default_sites: List[str]
    description: str

TENANTS: Dict[str, TenantConfig] = {
    "oil_india": TenantConfig(
        tenant_id="oil_india",
        company_name="Oil India Limited (OIL)",
        display_title="Oil India Limited — Upstream & Field Asset Division",
        primary_color="#0F172A",
        accent_color="#F59E0B",
        life_saving_rules=[
            "ENERGY_ISOLATION",
            "WORK_AUTHORISATION",
            "BYPASSING_SAFETY_CONTROLS",
            "CONFINED_SPACE",
            "DRIVING",
            "HOT_WORK",
            "LINE_OF_FIRE",
            "SAFE_MECHANICAL_LIFTING",
            "WORKING_AT_HEIGHT"
        ],
        scoring_weights={
            "exposure": 2.0,
            "energy": 1.0,
            "barrier": 1.2,
            "proximity": 1.0,
            "activity": 0.8
        },
        default_sites=[
            "Field Site 4 - Duliajan Central",
            "Moran Oilfield Well #84",
            "Naharkatiya Production Hub",
            "Jorajan Gas Compressor Station",
            "Kumchai Well Site 2",
            "Digboi Heritage Rig #03"
        ],
        description="Default national operator tenant (Oil India Limited). Standard IOGP 9 Life-Saving Rules and 5-Factor SIF Scoring."
    ),
    "ongc": TenantConfig(
        tenant_id="ongc",
        company_name="Oil and Natural Gas Corporation (ONGC)",
        display_title="ONGC — Offshore & Onshore Production Basin",
        primary_color="#1E293B",
        accent_color="#EF4444",
        life_saving_rules=[
            "ENERGY_ISOLATION",
            "WORK_AUTHORISATION",
            "BYPASSING_SAFETY_CONTROLS",
            "CONFINED_SPACE",
            "DRIVING",
            "HOT_WORK",
            "LINE_OF_FIRE",
            "SAFE_MECHANICAL_LIFTING",
            "WORKING_AT_HEIGHT",
            "MOC_MANAGEMENT_OF_CHANGE"
        ],
        scoring_weights={
            "exposure": 2.2,
            "energy": 1.1,
            "barrier": 1.3,
            "proximity": 1.0,
            "activity": 0.9
        },
        default_sites=[
            "Mumbai High Offshore Platform North",
            "Heera Asset Process Complex",
            "Basin Deepwater Rig KG-DWN",
            "Mehsana Asset Central Gathering"
        ],
        description="Integrated E&P operator with extended offshore Management of Change (MOC) controls and stricter barrier penalty weights."
    ),
    "global_ep": TenantConfig(
        tenant_id="global_ep",
        company_name="Global Energy & Drilling Contractors",
        display_title="Industry Standard Operator (Generic Upstream/Midstream)",
        primary_color="#0F2D37",
        accent_color="#06B6D4",
        life_saving_rules=[
            "ENERGY_ISOLATION",
            "WORK_AUTHORISALION",
            "BYPASSING_SAFETY_CONTROLS",
            "CONFINED_SPACE",
            "DRIVING",
            "HOT_WORK",
            "LINE_OF_FIRE",
            "SAFE_MECHANICAL_LIFTING",
            "WORKING_AT_HEIGHT"
        ],
        scoring_weights={
            "exposure": 2.0,
            "energy": 1.0,
            "barrier": 1.2,
            "proximity": 1.0,
            "activity": 0.8
        },
        default_sites=[
            "North Sea Platform Bravo",
            "Permian Basin Pad #12",
            "Rotterdam Midstream Terminal",
            "Gulf Coast Deepwater Drillship"
        ],
        description="Standard generic multi-operator template suitable for downstream refineries, drilling contractors, and midstream operators."
    )
}

def get_tenant_config(tenant_id: str = "oil_india") -> TenantConfig:
    return TENANTS.get(tenant_id, TENANTS["oil_india"])
