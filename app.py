import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import datetime
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import tempfile
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///invoices.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def number_to_french_words(n):
    """Convert a number to French words."""
    if n == 0:
        return "zéro"
    
    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    teens = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
    
    def convert_hundreds(num):
        result = ""
        if num >= 100:
            if num // 100 == 1:
                result += "cent"
            else:
                result += units[num // 100] + " cent"
            if num % 100 == 0 and num // 100 > 1:
                result += "s"
            num %= 100
            if num > 0:
                result += " "
        
        if num >= 20:
            if num < 70:
                result += tens[num // 10]
                if num % 10 > 0:
                    if num // 10 == 2 and num % 10 == 1:
                        result += " et un"
                    else:
                        result += "-" + units[num % 10]
            elif num < 80:
                result += "soixante"
                if num % 10 > 0:
                    if num % 10 < 10:
                        result += "-" + units[num % 10]
                    else:
                        result += "-" + teens[num % 10]
            else:
                if num < 90:
                    result += "quatre-vingt"
                    if num % 10 > 0:
                        result += "-" + units[num % 10]
                    elif num == 80:
                        result += "s"
                else:
                    result += "quatre-vingt"
                    if num % 10 < 10:
                        result += "-" + units[num % 10]
                    else:
                        result += "-" + teens[num % 10]
        elif num >= 10:
            result += teens[num - 10]
        elif num > 0:
            result += units[num]
        
        return result
    
    if n < 1000:
        return convert_hundreds(n)
    elif n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        result = ""
        if thousands == 1:
            result = "mille"
        else:
            result = convert_hundreds(thousands) + " mille"
        if remainder > 0:
            result += " " + convert_hundreds(remainder)
        return result
    else:
        millions = n // 1000000
        remainder = n % 1000000
        result = ""
        if millions == 1:
            result = "un million"
        else:
            result = convert_hundreds(millions) + " millions"
        if remainder > 0:
            if remainder >= 1000:
                result += " " + number_to_french_words(remainder)
            else:
                result += " " + convert_hundreds(remainder)
        return result

def find_column(df_columns, possible_names):
    """Find a column name from a list of possible variations."""
    df_columns_lower = [col.lower().strip() for col in df_columns]
    for possible in possible_names:
        for i, col_lower in enumerate(df_columns_lower):
            if possible.lower() in col_lower or col_lower in possible.lower():
                return df_columns[i]
    return None

def generer_factures_pdf(fichier_excel, factures_par_page=1, fixed_invoice_number="FAC-001", invoice_date=None, company_name="", address="", rc_name="", nif="", item_name="", client_profession="", month_year="", rib="", unit_price=0.0):
    """
    Generate PDF invoices from Excel data with fixed invoice number.
    Returns the path to the generated PDF file.
    """
    try:
        # Read Excel file
        df = pd.read_excel(fichier_excel)
        
        # Find column mappings with flexible matching
        name_variations = ['nom', 'nom prenom', 'client', 'name']
        quantity_variations = ['quantité', 'quantity', 'qte', 'qty']
        amount_variations = ['montant', 'amount', 'prix', 'price', 'total']
        
        name_col = find_column(df.columns, name_variations)
        quantity_col = find_column(df.columns, quantity_variations)
        amount_col = find_column(df.columns, amount_variations)
        
        # Validate required columns
        missing_columns = []
        if not name_col:
            missing_columns.append('Nom (ou nom prenom, client)')
        if not quantity_col:
            missing_columns.append('Quantité (ou quantity, qte)')
        if not amount_col:
            missing_columns.append('Montant (ou amount, prix)')
        
        if missing_columns:
            available_cols = ', '.join(df.columns)
            raise ValueError(f"Colonnes manquantes dans le fichier Excel: {', '.join(missing_columns)}. Colonnes disponibles: {available_cols}")
        
        # Check if dataframe is empty
        if df.empty:
            raise ValueError("Le fichier Excel est vide ou ne contient pas de données valides.")
        
        # Use provided date or today's date
        if invoice_date:
            today = datetime.datetime.strptime(invoice_date, '%Y-%m-%d').strftime('%d/%m/%Y')
        else:
            today = datetime.date.today().strftime("%d/%m/%Y")
        
        # Use the fixed invoice number for ALL invoices
        invoice_display = fixed_invoice_number
        
        # Create temporary PDF file
        pdf_path = os.path.join(tempfile.gettempdir(), f"factures_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        largeur, hauteur = A4
        
        factures_par_ligne = 2 if factures_par_page == 4 else 1
        factures_par_col = factures_par_page // factures_par_ligne
        largeur_facture = largeur / factures_par_ligne
        hauteur_facture = hauteur / factures_par_col

        for i, row in df.iterrows():
            pos_x = (i % factures_par_ligne) * largeur_facture
            pos_y = hauteur - ((i // factures_par_ligne) % factures_par_col + 1) * hauteur_facture

            # Draw invoice frame
            c.rect(pos_x+10, pos_y+10, largeur_facture-20, hauteur_facture-20)
            
            # Client header (top line)
            y_pos = pos_y + hauteur_facture - 30
            c.setFont("Helvetica", 10)
            c.drawString(pos_x+20, y_pos, f"NOM ET PRENOM:                 {row[name_col].upper()}                   PROFESSION: {client_profession}")
            
            # Invoice number and month (centered)
            y_pos -= 40
            c.setFont("Helvetica-Bold", 12)
            invoice_text = f"FACTURE N°:"
            text_width = c.stringWidth(invoice_text, "Helvetica-Bold", 12)
            c.drawString(pos_x + (largeur_facture - text_width)/2, y_pos, invoice_text)
            y_pos -= 15
            text_width = c.stringWidth(invoice_display, "Helvetica-Bold", 12)
            c.drawString(pos_x + (largeur_facture - text_width)/2, y_pos, invoice_display)
            y_pos -= 15
            c.setFont("Helvetica", 10)
            month_text = f"MOIS : {month_year}"
            text_width = c.stringWidth(month_text, "Helvetica", 10)
            c.drawString(pos_x + (largeur_facture - text_width)/2, y_pos, month_text)
            
            # Company details section
            y_pos -= 35
            c.setFont("Helvetica-Bold", 11)
            c.drawString(pos_x+20, y_pos, f"DOIT : {company_name}")
            y_pos -= 15
            c.setFont("Helvetica", 9)
            c.drawString(pos_x+20, y_pos, f"ADRESSE: {address}")
            y_pos -= 12
            c.drawString(pos_x+20, y_pos, f" RC:{rc_name}    NIF: {nif}            RIB : {rib}")
            
            # Table with borders
            y_pos -= 35
            table_start_y = y_pos
            table_height = 60
            
            # Table columns positions (removed avance column)
            col1_x = pos_x + 20   # Désignation
            col2_x = pos_x + 200  # Quantité/LITRE
            col3_x = pos_x + 280  # P.U
            col4_x = pos_x + 350  # Total
            table_end_x = pos_x + largeur_facture - 30
            
            # Draw table borders
            c.rect(col1_x, y_pos - table_height, table_end_x - col1_x, table_height)
            # Vertical lines
            c.line(col2_x, y_pos, col2_x, y_pos - table_height)
            c.line(col3_x, y_pos, col3_x, y_pos - table_height)
            c.line(col4_x, y_pos, col4_x, y_pos - table_height)
            # Horizontal line for header
            c.line(col1_x, y_pos - 25, table_end_x, y_pos - 25)
            
            # Table header
            c.setFont("Helvetica-Bold", 9)
            c.drawString(col2_x + 5, y_pos - 10, "Quantité/LITR")
            c.drawString(pos_x + 25, y_pos - 22, "Désignation")
            c.drawString(col2_x + 25, y_pos - 22, "E")
            c.drawString(col3_x + 10, y_pos - 22, "P.U")
            c.drawString(col4_x + 15, y_pos - 22, "Total")
            
            # Table content
            y_pos -= 40
            c.setFont("Helvetica", 9)
            quantity = float(row[quantity_col])
            total = quantity * unit_price
            
            c.drawString(col1_x + 5, y_pos, item_name)
            c.drawString(col2_x + 15, y_pos, str(int(quantity)))
            c.drawString(col3_x + 10, y_pos, f"{unit_price:.2f}")
            c.drawString(col4_x + 10, y_pos, f"{total:,.2f}")
            
            # Amount section
            y_pos -= 35
            c.setFont("Helvetica-Bold", 10)
            c.drawString(col3_x, y_pos, f"Montant                        {total:,.2f}")
            
            # Amount in French words
            y_pos -= 20
            c.setFont("Helvetica", 8)
            amount_words = number_to_french_words(int(total))
            c.drawString(pos_x + 20, y_pos, f"Arrêté la présente facture à la somme de : {amount_words} dinars")

            if (i+1) % factures_par_page == 0:
                c.showPage()

        c.save()
        return pdf_path
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération du PDF: {str(e)}")
        raise

@app.route('/')
def index():
    """Main page with file upload form."""
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    # Import models here to avoid circular imports
    from models import CompanySettings
    
    # Get saved company settings
    settings = CompanySettings.query.first()
    
    return render_template('index.html', today=today, settings=settings)

@app.route('/save_settings', methods=['POST'])
def save_settings():
    """Save company settings to database."""
    from models import CompanySettings
    
    try:
        # Get existing settings or create new
        settings = CompanySettings.query.first()
        if not settings:
            settings = CompanySettings()
        
        # Update settings from form
        settings.company_name = request.form.get('company_name', '')
        settings.address = request.form.get('address', '')
        settings.rc_name = request.form.get('rc_name', '')
        settings.nif = request.form.get('nif', '')
        settings.item_name = request.form.get('item_name', '')
        settings.client_profession = request.form.get('client_profession', '')
        settings.rib = request.form.get('rib', '')
        settings.unit_price = float(request.form.get('unit_price', 0))
        
        db.session.add(settings)
        db.session.commit()
        
        flash('Paramètres sauvegardés avec succès!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
        flash(f'Erreur lors de la sauvegarde: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate_invoices():
    """Generate PDF invoices from uploaded Excel file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(url_for('index'))
        
        if not file or not allowed_file(file.filename):
            flash('Type de fichier non autorisé. Veuillez utiliser un fichier Excel (.xlsx ou .xls)', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_file_path)
        
        # Get form parameters
        factures_par_page = int(request.form.get('factures_par_page', 1))
        fixed_invoice_number = request.form.get('fixed_invoice_number', 'FAC-001')  # Fixed invoice number
        invoice_date = request.form.get('invoice_date')
        month_year = request.form.get('month_year', '')
        
        # Company information
        company_name = request.form.get('company_name', '')
        address = request.form.get('address', '')
        rc_name = request.form.get('rc_name', '')
        nif = request.form.get('nif', '')
        item_name = request.form.get('item_name', '')
        client_profession = request.form.get('client_profession', '')
        rib = request.form.get('rib', '')
        unit_price = float(request.form.get('unit_price', 0))
        
        # Generate PDF
        pdf_path = generer_factures_pdf(
            fichier_excel=temp_file_path,
            factures_par_page=factures_par_page,
            fixed_invoice_number=fixed_invoice_number,  # Use fixed invoice number
            invoice_date=invoice_date,
            company_name=company_name,
            address=address,
            rc_name=rc_name,
            nif=nif,
            item_name=item_name,
            client_profession=client_profession,
            month_year=month_year,
            rib=rib,
            unit_price=unit_price
        )
        
        # Clean up temporary Excel file
        os.remove(temp_file_path)
        
        # Return PDF file
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'factures_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération: {str(e)}")
        flash(f'Erreur lors de la génération des factures: {str(e)}', 'error')
        return redirect(url_for('index'))

# Initialize database tables
with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
