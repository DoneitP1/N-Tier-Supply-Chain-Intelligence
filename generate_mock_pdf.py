import os
from fpdf import FPDF

def create_mock_contract(filename="bursa_supplier_contract.pdf"):
    """
    Generates a 2-page dummy supply chain contract PDF using fpdf.
    Contains realistic text about a Katman-1 supplier in Bursa.
    """
    pdf = FPDF()
    
    # --- PAGE 1 ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Tier-1 Supplier Contract - Bursa Manufacturing", ln=True, align="C")
    
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    
    content_page_1 = (
        "Supplier Name: Katman-1 Bursa Auto Parts Ltd.\n"
        "Location: Bursa, Turkey\n"
        "Effective Date: March 15, 2026\n\n"
        "1. OBLIGATIONS AND SUPPLY PARAMETERS\n"
        "The Supplier agrees to manufacture and supply the following components according "
        "to the specifications provided by the Buyer:\n\n"
        "Part Codes and Details:\n"
        "- Part Code: BMT-8900-X (Drive Shaft Assembly)\n"
        "  Lead Time: 14 days\n"
        "  Minimum Stock Units: 500 units\n\n"
        "- Part Code: BMT-8902-Y (Steering Column)\n"
        "  Lead Time: 21 days\n"
        "  Minimum Stock Units: 300 units\n\n"
        "2. QUALITY ASSURANCE\n"
        "The Supplier shall maintain ISO 9001 certification and allow unannounced "
        "quality inspections by the Buyer."
    )
    pdf.multi_cell(0, 10, content_page_1)
    
    # --- PAGE 2 ---
    pdf.add_page()
    
    content_page_2 = (
        "3. FORCE MAJEURE\n"
        "Neither party shall be liable for any failure or delay in performance under this "
        "Agreement to the extent said failures or delays are proximately caused by causes "
        "beyond that party's reasonable control and occurring without its fault or negligence, "
        "including, without limitation, failure of suppliers, subcontractors, and carriers. "
        "Provided that, as a condition to the claim of non-liability, the party experiencing "
        "the difficulty shall give the other prompt written notice, with full details "
        "following the occurrence of the cause relied upon.\n\n"
        "4. ALTERNATIVE SUPPLIER PROTOCOL\n"
        "In the event that the Supplier is unable to fulfill a Purchase Order due to a Force "
        "Majeure event or other significant operational disruption extending past 7 days, "
        "the Buyer retains the right to use alternative suppliers without penalty. The Supplier "
        "is authorized to outsource up to 15% of the capacity to an approved Alternative "
        "Supplier list if written notice is provided.\n\n\n"
        "Signatures:\n\n"
        "_______________________               _______________________\n"
        "Supplier Representative                 Buyer Representative\n"
        "Katman-1 Bursa Auto Parts               N-Tier Supply Chain Co."
    )
    pdf.multi_cell(0, 10, content_page_2)
    
    # Save the PDF
    pdf.output(filename)
    print(f"✅ Mock PDF successfully generated: {os.path.abspath(filename)}")

if __name__ == "__main__":
    create_mock_contract()
