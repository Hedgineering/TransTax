from borb.pdf import Document
from borb.pdf import PDF
from borb.pdf import Page
from borb.pdf.canvas.layout.table.fixed_column_width_table import FixedColumnWidthTable as Table
from borb.pdf import FlexibleColumnWidthTable as Table2
from borb.pdf.canvas.layout.text.paragraph import Paragraph
from borb.pdf.canvas.layout.layout_element import Alignment
from borb.pdf.canvas.layout.table.table import TableCell
from borb.pdf.canvas.layout.page_layout.multi_column_layout import MultiColumnLayout
from borb.pdf.canvas.layout.image.image import Image
from borb.pdf.canvas.color.color import HexColor, X11Color
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

PAD: int = 2
FONT_SIZE: int = 12

def _break_text(text: str, n: int):
    return

# add company info
def _build_invoice_information(inv_date, inv_num, due_date, 
                               company_street, company_region, company_phone, company_email, company_website):    
    # REPLACE IF BUGS: num_rows: int = 5 - (company_email == None) - (company_website == None)
    num_rows: int = 5 - (not company_email) - (not company_website)
    table_001 = Table(number_of_rows=num_rows, number_of_columns=3)
    
    table_001.add(Paragraph(company_street))    
    table_001.add(Paragraph("Date:", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT))  

    table_001.add(Paragraph("%d/%d/%d" % (inv_date.month, inv_date.day, inv_date.year)))
    
    table_001.add(Paragraph(company_region))    
    table_001.add(Paragraph("Invoice Number:", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT))
    table_001.add(Paragraph(inv_num))   
    
    table_001.add(Paragraph(company_phone))    
    table_001.add(Paragraph("Due Date:", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT))
    table_001.add(Paragraph("%d/%d/%d" % (due_date.month, due_date.day, due_date.year))) 

    if company_email:
        table_001.add(Paragraph(company_email))    
        table_001.add(Paragraph(" "))
        table_001.add(Paragraph(" "))
    if company_website:
        table_001.add(Paragraph(company_website))
        table_001.add(Paragraph(" "))
        table_001.add(Paragraph(" "))
    table_001.set_padding_on_all_cells(Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD))    		
    table_001.no_borders()
    return table_001


# add billing information
def _build_billing_and_shipping_information(bill_name, bill_street, bill_region, bill_phone,
                                            ship_name, ship_street, ship_region, ship_phone):  
    table_001 = Table(number_of_rows=5, number_of_columns=2)  
    table_001.add(Paragraph("Bill To:", font="Helvetica-Bold"))  
    table_001.add(Paragraph("Ship To:", font="Helvetica-Bold"))  
    table_001.add(Paragraph(str(bill_name)))         # BILLING  
    table_001.add(Paragraph(str(ship_name)))         # SHIPPING  
    table_001.add(Paragraph(str(bill_street)))       # BILLING  
    table_001.add(Paragraph(str(ship_street)))       # SHIPPING  
    table_001.add(Paragraph(str(bill_region)))       # BILLING  
    table_001.add(Paragraph(str(ship_region)))       # SHIPPING  
    table_001.add(Paragraph(str(bill_phone)))        # BILLING  
    table_001.add(Paragraph(str(ship_phone)))        # SHIPPING  
    table_001.set_padding_on_all_cells(Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD))  
    table_001.no_borders()  
    return table_001

def _build_itemized_description_table(group):
    table_001 = Table(
        number_of_rows=group.shape[0] + 2, 
        number_of_columns=7,
        column_widths=[Decimal(4), Decimal(2), Decimal(2.5), Decimal(2.5), Decimal(2), Decimal(2.5), Decimal(2.5)]
    )  
    for h in ["Product Description", "Quantity", "Product Price", "Exempt", "Tax Rate", "Tax Amount", "Total Price"]:  
        table_001.add(
            TableCell(  
                Paragraph(h, font_color=X11Color("White")),  
                background_color=HexColor("14396b"),  
            )  
        )  
    odd_color = HexColor("BBBBBB")  
    even_color = HexColor("FFFFFF")
    for index, row in group.iterrows():  
        c = even_color if index % 2 == 0 else odd_color  
        table_001.add(TableCell(Paragraph(str(row["Product"]),              font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph(str(row["Quantity"]),             font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph("$ " + str(row["GrossAmount"]),   font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph("$ " + str(row["ExemptAmount"]),  font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph(str(row["TaxRate"]*100) + " %",   font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph("$ " + str(row["TaxAmount"]),     font_size=FONT_SIZE), background_color=c))
        table_001.add(TableCell(Paragraph("$ " + str(row["Total"]),         font_size=FONT_SIZE), background_color=c))
    table_001.add(TableCell(Paragraph("Total", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT), column_span=6))  
    table_001.add(TableCell(Paragraph("$ " + str(group["Total"].sum()), horizontal_alignment=Alignment.RIGHT)))  
    table_001.set_padding_on_all_cells(Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD))  
    return table_001




"""
Expected Spreadsheet Columns:

(1) Invoice Date

"""


def main(fileName: str="AE Sample data.xlsx", 
         fileHeader: int=0,
         logo: str="https://1000logos.net/wp-content/uploads/2019/03/IEEE-Logo.jpg"):
    # read xlsx; interpolate missing columns, building complete ShipTo and BillTo addresses
    df = pd.read_excel(fileName, header=fileHeader)

    df["Quantity"].fillna(1, inplace=True)
    df["TaxRate"].fillna(0.05, inplace=True)
    if "TaxAmount" not in df.columns:
        df["TaxAmount"] = (df["GrossAmount"] - df["ExemptAmount"])*df["TaxRate"]
    if "Total" not in df.columns:
        df["Total"] = df["GrossAmount"] + df["TaxAmount"]
    if "BillToName" not in df.columns:
        df["BillToName"] = "-"
    if "BillToState" not in df.columns:
        df["BillToRegion"] = (
            np.where(~df["BillToState"].isna(), 
                    df["BillToState"] + ", ", 
                    "") +
            df["BILL TO COUNTRY"] +
            " " +
            df["BillToZip"]
        )

    df["BillToPhone"].fillna("-", inplace=True)
    df["ShipToName"].fillna("-", inplace=True)
    if "ShipToState" not in df.columns:
        df["ShipToRegion"] = (
            np.where(~df["ShipToCity"].isna(), 
                    df["ShipToCity"] + ", ", 
                    "") +
            df["ShipToCountry"] +
            " " +
            df["ShipToZip"]
        )
    df["ShipToPhone"].fillna("-", inplace=True)


    # group together invoice rows by invoice number, summing quantites for the same products
    # grouped = df.groupby(["InvoiceNumber", "Product"]).agg({"Quantity": "sum"}).groupby("InvoiceNumber")
    grouped = df.groupby("InvoiceNumber", as_index=False)

    print("Creating invoices...")

    # generate unique invoice for each group
    for i, (name, group) in enumerate(grouped):

        if i == 1:
            return
        
        group = group.reset_index()

        # create pdf
        pdf = Document()
        page = Page()
        pdf.add_page(page)

        page_layout = MultiColumnLayout(page,
                                        column_widths=[page.get_page_info().get_width() - Decimal(72)],
                                        margin_top=Decimal(36),
                                        margin_right=Decimal(36),
                                        margin_bottom=Decimal(36),
                                        margin_left=Decimal(36))

        # add top logo
        page_layout.add(Image(logo,
                              width=Decimal(192),
                              height=Decimal(128)))

        try:
            # add company info  
            page_layout.add(_build_invoice_information(group.loc[0]["#InvoiceDate"], name, group.loc[0]["#InvoiceDate"],
                                                    "445 Hoes Lane", "Piscataway, NJ 08854", "+1 732 981 0060", "society-info@ieee.org", "ieee.org"))

            # empty paragraph for spacing
            page_layout.add(Paragraph(" "))

            # add billing/shipping addresses
            page_layout.add(_build_billing_and_shipping_information(group.loc[0]["BillToName"], group.loc[0]["BillToAddress"], group.loc[0]["BillToRegion"], group.loc[0]["BillToPhone"],
                                                                    group.loc[0]["ShipToName"], group.loc[0]["ShipToAddress"], group.loc[0]["ShipToRegion"], group.loc[0]["ShipToPhone"]))

            # add invoice info
            page_layout.add(_build_itemized_description_table(group))

            # save pdf
            with open(f"invoice{i + 1}.pdf", "wb") as pdf_file_handle:
                PDF.dumps(pdf_file_handle, pdf)

            print(f"Invoice {i + 1} created")
        except Exception as e:
            print(f"Invoice {i + 1} failed!\n{e}\n")

    print("Done!")


if __name__ == "__main__":
    main()