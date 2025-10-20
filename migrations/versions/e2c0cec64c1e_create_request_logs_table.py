from alembic import op
import sqlalchemy as sa

revision = "xxxxxxxxx""  # mantém o mesmo hash"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "request_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("method", sa.String(length=10)),
        sa.Column("path", sa.String(length=255)),
        sa.Column("status_code", sa.Integer()),
        sa.Column("ip", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("ms_email", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
    )

def downgrade():
    op.drop_table("request_logs")