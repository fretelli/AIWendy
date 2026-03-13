"""RPG gamification: trading characters, achievements, quests, leaderboard.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    rank_enum = postgresql.ENUM('bronze', 'silver', 'gold', 'platinum', 'diamond', name='rank', create_type=False)
    achievement_category_enum = postgresql.ENUM('trading', 'discipline', 'milestones', 'streaks', name='achievementcategory', create_type=False)
    achievement_rarity_enum = postgresql.ENUM('common', 'rare', 'epic', 'legendary', name='achievementrarity', create_type=False)
    quest_type_enum = postgresql.ENUM('daily', 'weekly', 'special', name='questtype', create_type=False)
    quest_status_enum = postgresql.ENUM('active', 'completed', 'expired', name='queststatus', create_type=False)
    period_type_enum = postgresql.ENUM('weekly', 'monthly', name='periodtype', create_type=False)

    rank_enum.create(op.get_bind(), checkfirst=True)
    achievement_category_enum.create(op.get_bind(), checkfirst=True)
    achievement_rarity_enum.create(op.get_bind(), checkfirst=True)
    quest_type_enum.create(op.get_bind(), checkfirst=True)
    quest_status_enum.create(op.get_bind(), checkfirst=True)
    period_type_enum.create(op.get_bind(), checkfirst=True)

    # trading_characters
    op.create_table(
        'trading_characters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('nickname', sa.String(50), nullable=True),
        sa.Column('avatar_settings', postgresql.JSON(), server_default='{}'),
        sa.Column('discipline', sa.Integer(), server_default='50'),
        sa.Column('patience', sa.Integer(), server_default='50'),
        sa.Column('risk_management', sa.Integer(), server_default='50'),
        sa.Column('decisiveness', sa.Integer(), server_default='50'),
        sa.Column('consistency', sa.Integer(), server_default='50'),
        sa.Column('level', sa.Integer(), server_default='1'),
        sa.Column('xp', sa.Integer(), server_default='0'),
        sa.Column('rank', rank_enum, server_default='bronze'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # achievements
    op.create_table(
        'achievements',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', achievement_category_enum, nullable=False),
        sa.Column('rarity', achievement_rarity_enum, nullable=False),
        sa.Column('icon', sa.String(10), server_default=''),
        sa.Column('criteria', postgresql.JSON(), nullable=False),
        sa.Column('xp_reward', sa.Integer(), server_default='10'),
    )

    # user_achievements
    op.create_table(
        'user_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('achievement_id', sa.String(50), sa.ForeignKey('achievements.id'), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('trade_context', postgresql.JSON(), nullable=True),
        sa.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )

    # quests
    op.create_table(
        'quests',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quest_type', quest_type_enum, nullable=False),
        sa.Column('criteria', postgresql.JSON(), nullable=False),
        sa.Column('xp_reward', sa.Integer(), server_default='20'),
    )

    # user_quests
    op.create_table(
        'user_quests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('quest_id', sa.String(50), sa.ForeignKey('quests.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress', postgresql.JSON(), server_default='{}'),
        sa.Column('status', quest_status_enum, server_default='active'),
    )
    op.create_index('ix_user_quests_user_status', 'user_quests', ['user_id', 'status'])

    # leaderboard_entries
    op.create_table(
        'leaderboard_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('period_type', period_type_enum, nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('xp', sa.Integer(), server_default='0'),
        sa.Column('win_rate', sa.Float(), server_default='0'),
        sa.Column('profit_factor', sa.Float(), server_default='0'),
        sa.Column('achievement_count', sa.Integer(), server_default='0'),
        sa.Column('rank_position', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'period_type', 'period_start', name='uq_leaderboard_entry'),
    )
    op.create_index('ix_leaderboard_period', 'leaderboard_entries', ['period_type', 'period_start'])

    # Seed achievements and quests using raw SQL (asyncpg requires explicit casts for enums)
    from domain.rpg.seed import ACHIEVEMENTS, QUESTS
    import json

    for a in ACHIEVEMENTS:
        criteria_json = json.dumps(a['criteria']).replace("'", "''")
        name = a['name'].replace("'", "''")
        desc = a['description'].replace("'", "''")
        op.execute(
            f"INSERT INTO achievements (id, name, description, category, rarity, icon, criteria, xp_reward) "
            f"VALUES ('{a['id']}', '{name}', '{desc}', "
            f"'{a['category']}'::achievementcategory, '{a['rarity']}'::achievementrarity, "
            f"'{a['icon']}', '{criteria_json}'::json, {a['xp_reward']})"
        )

    for q in QUESTS:
        criteria_json = json.dumps(q['criteria']).replace("'", "''")
        name = q['name'].replace("'", "''")
        desc = q['description'].replace("'", "''")
        op.execute(
            f"INSERT INTO quests (id, name, description, quest_type, criteria, xp_reward) "
            f"VALUES ('{q['id']}', '{name}', '{desc}', "
            f"'{q['quest_type']}'::questtype, '{criteria_json}'::json, {q['xp_reward']})"
        )


def downgrade() -> None:
    op.drop_table('leaderboard_entries')
    op.drop_table('user_quests')
    op.drop_table('quests')
    op.drop_table('user_achievements')
    op.drop_table('achievements')
    op.drop_table('trading_characters')

    op.execute('DROP TYPE IF EXISTS rank')
    op.execute('DROP TYPE IF EXISTS achievementcategory')
    op.execute('DROP TYPE IF EXISTS achievementrarity')
    op.execute('DROP TYPE IF EXISTS questtype')
    op.execute('DROP TYPE IF EXISTS queststatus')
    op.execute('DROP TYPE IF EXISTS periodtype')
