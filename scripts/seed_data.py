"""Seed local SQLite databases with sample patient data for development.

Creates sample patients, providers, time slots, vitals, conditions,
and consent records so the platform can be exercised end-to-end.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from src.core.config import get_settings
from src.core.consent.manager import store_consent
from src.core.consent.models import (
    ConsentRecord,
    ConsentScope,
    ConsentStatus,
)
from src.core.database.engine import get_engine
from src.models.fhir.condition import ClinicalStatus
from src.models.fhir.patient import ContactInfo, Gender

settings = get_settings()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

PATIENTS = [
    {
        "id": "patient-001",
        "mrn": "MRN-10001",
        "given_name": "Alice",
        "family_name": "Johnson",
        "birth_date": "1985-03-15",
        "gender": Gender.FEMALE,
        "contact": ContactInfo(
            phone="555-0101",
            email="alice.johnson@example.com",
            city="Springfield",
            state="IL",
            postal_code="62701",
        ),
    },
    {
        "id": "patient-002",
        "mrn": "MRN-10002",
        "given_name": "Bob",
        "family_name": "Martinez",
        "birth_date": "1972-08-22",
        "gender": Gender.MALE,
        "contact": ContactInfo(
            phone="555-0102",
            email="bob.martinez@example.com",
            city="Shelbyville",
            state="IL",
            postal_code="62565",
        ),
    },
    {
        "id": "patient-003",
        "mrn": "MRN-10003",
        "given_name": "Carol",
        "family_name": "Williams",
        "birth_date": "1990-11-05",
        "gender": Gender.FEMALE,
        "contact": ContactInfo(
            phone="555-0103",
            email="carol.williams@example.com",
            city="Capital City",
            state="IL",
            postal_code="62701",
        ),
    },
    {
        "id": "patient-004",
        "mrn": "MRN-10004",
        "given_name": "David",
        "family_name": "Chen",
        "birth_date": "1968-01-30",
        "gender": Gender.MALE,
        "contact": ContactInfo(
            phone="555-0104",
            email="david.chen@example.com",
            city="Springfield",
            state="IL",
            postal_code="62704",
        ),
    },
    {
        "id": "patient-005",
        "mrn": "MRN-10005",
        "given_name": "Eva",
        "family_name": "Thompson",
        "birth_date": "1995-06-18",
        "gender": Gender.FEMALE,
        "contact": ContactInfo(
            phone="555-0105",
            email="eva.thompson@example.com",
            city="Springfield",
            state="IL",
            postal_code="62702",
        ),
    },
]

PROVIDERS = [
    {
        "id": "provider-001",
        "name": "Dr. Sarah Kim",
        "specialty": "Internal Medicine",
        "department": "Primary Care",
    },
    {
        "id": "provider-002",
        "name": "Dr. James Patel",
        "specialty": "Cardiology",
        "department": "Cardiology",
    },
    {
        "id": "provider-003",
        "name": "Dr. Maria Santos",
        "specialty": "Emergency Medicine",
        "department": "Emergency",
    },
    {
        "id": "provider-004",
        "name": "Dr. Robert Lee",
        "specialty": "Orthopedics",
        "department": "Orthopedics",
    },
    {
        "id": "provider-005",
        "name": "Dr. Emily Brown",
        "specialty": "Neurology",
        "department": "Neurology",
    },
]

CONDITIONS = [
    {
        "id": "cond-001",
        "patient_id": "patient-001",
        "icd10_code": "I10",
        "snomed_code": "38341003",
        "display_name": "Essential hypertension",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2020-06-01",
    },
    {
        "id": "cond-002",
        "patient_id": "patient-002",
        "icd10_code": "E11.9",
        "snomed_code": "44054006",
        "display_name": "Type 2 diabetes mellitus",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2018-03-15",
    },
    {
        "id": "cond-003",
        "patient_id": "patient-002",
        "icd10_code": "I10",
        "snomed_code": "38341003",
        "display_name": "Essential hypertension",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2019-01-20",
    },
    {
        "id": "cond-004",
        "patient_id": "patient-003",
        "icd10_code": "J45.20",
        "snomed_code": "195967001",
        "display_name": "Mild intermittent asthma",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2015-09-10",
    },
    {
        "id": "cond-005",
        "patient_id": "patient-004",
        "icd10_code": "M54.5",
        "snomed_code": "279039007",
        "display_name": "Low back pain",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2024-11-01",
    },
    {
        "id": "cond-006",
        "patient_id": "patient-004",
        "icd10_code": "I25.10",
        "snomed_code": "53741008",
        "display_name": "Coronary artery disease",
        "clinical_status": ClinicalStatus.ACTIVE,
        "onset_date": "2022-05-20",
    },
]

VITALS = [
    {
        "patient_id": "patient-001",
        "heart_rate": 78,
        "bp_sys": 142,
        "bp_dia": 88,
        "temp": 36.7,
        "resp": 16,
        "spo2": 98,
    },
    {
        "patient_id": "patient-002",
        "heart_rate": 82,
        "bp_sys": 155,
        "bp_dia": 95,
        "temp": 36.8,
        "resp": 18,
        "spo2": 97,
    },
    {
        "patient_id": "patient-003",
        "heart_rate": 72,
        "bp_sys": 118,
        "bp_dia": 76,
        "temp": 36.6,
        "resp": 14,
        "spo2": 99,
    },
    {
        "patient_id": "patient-004",
        "heart_rate": 88,
        "bp_sys": 138,
        "bp_dia": 85,
        "temp": 36.9,
        "resp": 17,
        "spo2": 96,
    },
    {
        "patient_id": "patient-005",
        "heart_rate": 68,
        "bp_sys": 112,
        "bp_dia": 72,
        "temp": 36.5,
        "resp": 15,
        "spo2": 99,
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

_INSERT_PATIENT = text("INSERT OR REPLACE INTO patients (id, data) VALUES (:id, :data)")
_INSERT_CONDITION = text(
    "INSERT OR REPLACE INTO conditions (id, patient_id, data) VALUES (:id, :pid, :data)"
)
_INSERT_OBSERVATION = text(
    "INSERT OR REPLACE INTO observations (id, patient_id, type, data)"
    " VALUES (:id, :pid, :type, :data)"
)
_INSERT_PROVIDER = text("INSERT OR REPLACE INTO providers (id, data) VALUES (:id, :data)")
_INSERT_SLOT = text(
    "INSERT OR REPLACE INTO time_slots (slot_id, provider_id, data) VALUES (:sid, :pid, :data)"
)


async def seed_fhir_db() -> None:
    """Seed the FHIR database with patients, conditions, and observations."""
    engine = get_engine("fhir")
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY, data JSON NOT NULL)")
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS conditions ("
                "id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
                "data JSON NOT NULL)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS observations ("
                "id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
                "type TEXT NOT NULL, data JSON NOT NULL)"
            )
        )

        for p in PATIENTS:
            row = {
                **p,
                "birth_date": p["birth_date"],
                "gender": p["gender"].value,
                "contact": p["contact"].model_dump(),
            }
            await conn.execute(
                _INSERT_PATIENT,
                {"id": p["id"], "data": json.dumps(row, default=str)},
            )
        print(f"  Seeded {len(PATIENTS)} patients")

        for c in CONDITIONS:
            await conn.execute(
                _INSERT_CONDITION,
                {
                    "id": c["id"],
                    "pid": c["patient_id"],
                    "data": json.dumps(c, default=str),
                },
            )
        print(f"  Seeded {len(CONDITIONS)} conditions")

        for i, v in enumerate(VITALS):
            obs_id = f"obs-vitals-{i + 1:03d}"
            await conn.execute(
                _INSERT_OBSERVATION,
                {
                    "id": obs_id,
                    "pid": v["patient_id"],
                    "type": "vitals",
                    "data": json.dumps(v, default=str),
                },
            )
        print(f"  Seeded {len(VITALS)} vital-sign observations")


async def seed_scheduling_db() -> None:
    """Seed the scheduling database with providers and time slots."""
    engine = get_engine("scheduling")
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE IF NOT EXISTS providers (id TEXT PRIMARY KEY, data JSON NOT NULL)")
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS time_slots ("
                "slot_id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, "
                "data JSON NOT NULL)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS appointments ("
                "id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
                "provider_id TEXT NOT NULL, data JSON NOT NULL)"
            )
        )

        for prov in PROVIDERS:
            await conn.execute(
                _INSERT_PROVIDER,
                {"id": prov["id"], "data": json.dumps(prov)},
            )
        print(f"  Seeded {len(PROVIDERS)} providers")

        now = datetime.now(UTC)
        base_date = now.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        slot_count = 0
        for prov in PROVIDERS:
            day_offset = 0
            days_added = 0
            while days_added < 5:
                slot_date = base_date + timedelta(days=day_offset)
                day_offset += 1
                if slot_date.weekday() >= 5:
                    continue
                days_added += 1
                for hour in (9, 10, 11, 14):
                    start = slot_date.replace(hour=hour)
                    end = start + timedelta(minutes=30)
                    fmt = start.strftime("%Y%m%d-%H%M")
                    slot_id = f"slot-{prov['id']}-{fmt}"
                    slot = {
                        "slot_id": slot_id,
                        "provider_id": prov["id"],
                        "start_time": start.isoformat(),
                        "end_time": end.isoformat(),
                        "is_available": True,
                    }
                    await conn.execute(
                        _INSERT_SLOT,
                        {
                            "sid": slot_id,
                            "pid": prov["id"],
                            "data": json.dumps(slot),
                        },
                    )
                    slot_count += 1
        print(f"  Seeded {slot_count} time slots")


def seed_consent() -> None:
    """Seed in-memory consent records for all patients."""
    agents = [
        "triage_agent",
        "care_coordinator",
        "clinical_data_agent",
        "pharmacy_agent",
    ]
    for p in PATIENTS:
        consent = ConsentRecord(
            consent_id=f"consent-{p['id']}",
            patient_id=p["id"],
            status=ConsentStatus.ACTIVE,
            scopes=[
                ConsentScope(
                    data_types=[
                        "demographics",
                        "labs",
                        "vitals",
                        "conditions",
                        "medications",
                    ],
                    permitted_uses=[
                        "treatment",
                        "care_coordination",
                    ],
                    permitted_agents=agents,
                ),
            ],
        )
        store_consent(consent)
    print(f"  Seeded {len(PATIENTS)} consent records (in-memory)")


async def main() -> None:
    print("Seeding local development databases...")
    print()

    settings.db_dir.mkdir(parents=True, exist_ok=True)

    print("[FHIR Database]")
    await seed_fhir_db()
    print()

    print("[Scheduling Database]")
    await seed_scheduling_db()
    print()

    print("[Consent Store]")
    seed_consent()
    print()

    print(f"Done. Database files in: {settings.db_dir}")


if __name__ == "__main__":
    asyncio.run(main())
