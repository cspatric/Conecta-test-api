"""autogen (fix constraints, add ms_oid, nullable password_hash, backfill uuid/name)

Revision ID: 4aa4a87fcf65
Revises: b76b09c881e0
Create Date: 2025-10-18 14:50:46.673889
"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '4aa4a87fcf65'
down_revision = 'b76b09c881e0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        # adiciona colunas com nullable provisório para poder fazer data migration
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('ms_oid', sa.String(length=64), nullable=True))

        # email passa a ser NOT NULL
        batch_op.alter_column('email',
                              existing_type=sa.VARCHAR(length=180),
                              nullable=False)

        # remove coluna antiga
        batch_op.drop_column('display_name')

    # data migration: preencher uuid e name para registros existentes
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id, email FROM users")).mappings().all()
    for row in users:
        # name: usa parte local do email se não houver nada
        local_name = (row["email"] or "").split("@")[0]
        conn.execute(
            sa.text("UPDATE users SET uuid=:uuid, name=:name WHERE id=:id"),
            {"uuid": str(uuid.uuid4()), "name": local_name or "user", "id": row["id"]},
        )

    # agora podemos forçar NOT NULL em uuid e name
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('uuid',
                              existing_type=sa.String(length=36),
                              nullable=False)
        batch_op.alter_column('name',
                              existing_type=sa.String(length=120),
                              nullable=False)

    # cria índice único nomeado para uuid (em vez de create_unique_constraint sem nome)
    op.create_index('ux_users_uuid', 'users', ['uuid'], unique=True)

    # se você quiser garantir unique em email nesta revisão e não existir ainda, descomente:
    # op.create_index('ux_users_email', 'users', ['email'], unique=True)


def downgrade():
    # drop índices criados
    op.drop_index('ux_users_uuid', table_name='users')
    # se criou o unique de email, descomente:
    # op.drop_index('ux_users_email', table_name='users')

    with op.batch_alter_table('users', schema=None) as batch_op:
        # voltar nullability
        batch_op.alter_column('name',
                              existing_type=sa.String(length=120),
                              nullable=True)
        batch_op.alter_column('uuid',
                              existing_type=sa.String(length=36),
                              nullable=True)
        batch_op.alter_column('email',
                              existing_type=sa.VARCHAR(length=180),
                              nullable=True)

        # remover colunas novas
        batch_op.drop_column('ms_oid')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('name')
        batch_op.drop_column('uuid')

        # restaurar display_name
        batch_op.add_column(sa.Column('display_name', sa.VARCHAR(length=120), nullable=True))