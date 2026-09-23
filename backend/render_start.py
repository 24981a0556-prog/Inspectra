"""
INSPECTRA — Render startup script
Runs DB migrations (ALTER TABLE) before starting the server.
Called by Render's startCommand via: python render_start.py
"""
import subprocess
import sys
import os


def run_migrations():
    """Apply Phase 2 schema additions using SQLAlchemy."""
    print("=== INSPECTRA: Running DB migrations ===")
    try:
        from app.core.database import engine
        from sqlalchemy import text

        migrations = [
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS analysis_error VARCHAR(2000)",
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE",
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS final_decision_comment VARCHAR(2000)",
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMPTZ",
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS finalized_by_id INTEGER REFERENCES users(id)",
        ]

        enum_migrations = [
            """
            DO $body$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'ANALYZING'
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'inspectionstatus')
                ) THEN
                    ALTER TYPE inspectionstatus ADD VALUE 'ANALYZING';
                END IF;
            END
            $body$
            """,
            """
            DO $body$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = 'CLOSED'
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'inspectionstatus')
                ) THEN
                    ALTER TYPE inspectionstatus ADD VALUE 'CLOSED';
                END IF;
            END
            $body$
            """,
            """
            DO $body$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'finaldecision') THEN
                    CREATE TYPE finaldecision AS ENUM (
                        'COMPLIANT', 'NON_COMPLIANT', 'REQUIRES_FURTHER_REVIEW'
                    );
                END IF;
            END
            $body$
            """,
            """
            DO $body$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'complianceseverity') THEN
                    CREATE TYPE complianceseverity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
                END IF;
            END
            $body$
            """,
            "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS final_decision finaldecision",
            """
            CREATE TABLE IF NOT EXISTS evidences (
                id SERIAL PRIMARY KEY,
                inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
                image_id INTEGER REFERENCES inspection_images(id),
                evidence_ref_id VARCHAR(20),
                agent_type VARCHAR(50),
                evidence_type VARCHAR(100),
                field_name VARCHAR(100),
                extracted_value VARCHAR(1000),
                bbox_x FLOAT, bbox_y FLOAT, bbox_width FLOAT, bbox_height FLOAT,
                ocr_text VARCHAR(1000),
                confidence FLOAT,
                extra_data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_evidences_inspection_id ON evidences(inspection_id)",
            "CREATE INDEX IF NOT EXISTS ix_evidences_evidence_ref_id ON evidences(evidence_ref_id)",
            """
            CREATE TABLE IF NOT EXISTS ai_results (
                id SERIAL PRIMARY KEY,
                inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
                agent_type VARCHAR(100) NOT NULL,
                input_image_id INTEGER REFERENCES inspection_images(id),
                result_json JSONB,
                confidence FLOAT,
                model_name VARCHAR(100),
                model_version VARCHAR(50),
                provider VARCHAR(50),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_ai_results_inspection_id ON ai_results(inspection_id)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS rule_version VARCHAR(20)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS rule_name VARCHAR(255)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS engine_type VARCHAR(50)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS severity complianceseverity",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS evidence_ref_ids JSONB",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS requires_human_review BOOLEAN DEFAULT FALSE",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS human_reviewed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS human_action VARCHAR(50)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS human_comment VARCHAR(2000)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS human_reviewer_id INTEGER REFERENCES users(id)",
            "ALTER TABLE compliance_checks ADD COLUMN IF NOT EXISTS human_reviewed_at TIMESTAMPTZ",
            "ALTER TABLE human_reviews ADD COLUMN IF NOT EXISTS compliance_check_id INTEGER REFERENCES compliance_checks(id)",
        ]

        with engine.connect() as conn:
            for sql in migrations + enum_migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"  [SKIP] {str(e).split(chr(10))[0][:80]}")

        print("=== Migrations complete ===")
    except Exception as e:
        print(f"Migration error: {e}")
        # Don't abort — let the app start anyway; create_all will handle new tables


if __name__ == "__main__":
    run_migrations()
    # Start uvicorn
    port = os.environ.get("PORT", "8000")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", port],
        check=True,
    )
