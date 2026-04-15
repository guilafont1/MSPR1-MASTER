import pdfplumber
import os

files = [
    'TPRE813_Bloc 3_Grille MSPR I1 EISI.pdf',
    'Régles validation MSPR.pdf',
    'TPRE813_Bloc 3_Sujet MSPR I1 EISI.pdf'
]

for f in files:
    print(f'========== {f} ==========')
    try:
        with pdfplumber.open(f) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    print(f'--- Page {i} ---')
                    print(text)
    except Exception as e:
        print(f'Erreur: {e}')
    print()
