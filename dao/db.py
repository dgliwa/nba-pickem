import os
import sqlalchemy as sa


engine = sa.create_engine(os.environ.get('DB_URL')) if os.environ.get('DB_URL') else None
