"""Add tema and tipo fields to quesitos table."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0021_quesitos_tema_tipo"
down_revision = "0020_technical_limitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tema and tipo columns to quesitos table."""
    op.add_column(
        "quesitos",
        sa.Column(
            "tema",
            sa.String(100),
            nullable=True,
            comment="Tema/assunto do quesito (ex: contábil, trabalhista, pericial)",
        ),
    )
    op.add_column(
        "quesitos",
        sa.Column(
            "tipo",
            sa.String(50),
            nullable=True,
            comment="Tipo de quesito (ex: técnico, jurídico, complementar)",
        ),
    )
    op.create_index(op.f("ix_quesitos_tema"), "quesitos", ["tema"], unique=False)
    op.create_index(op.f("ix_quesitos_tipo"), "quesitos", ["tipo"], unique=False)


def downgrade() -> None:
    """Remove tema and tipo columns from quesitos table."""
    op.drop_index(op.f("ix_quesitos_tipo"), table_name="quesitos")
    op.drop_index(op.f("ix_quesitos_tema"), table_name="quesitos")
    op.drop_column("quesitos", "tipo")
    op.drop_column("quesitos", "tema")
