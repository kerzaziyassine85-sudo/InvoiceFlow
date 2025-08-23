from app import db

class CompanySettings(db.Model):
    """Model to store company settings for invoice generation."""
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=True, default='')
    address = db.Column(db.Text, nullable=True, default='')
    rc_name = db.Column(db.String(100), nullable=True, default='')
    nif = db.Column(db.String(100), nullable=True, default='')
    item_name = db.Column(db.String(200), nullable=True, default='')
    client_profession = db.Column(db.String(100), nullable=True, default='')
    rib = db.Column(db.String(100), nullable=True, default='')
    unit_price = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<CompanySettings {self.company_name}>'
