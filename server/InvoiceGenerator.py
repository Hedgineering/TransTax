import os
import argostranslate.package
import argostranslate.translate
from borb.pdf import Document
from borb.pdf import PDF
from borb.pdf import Page
from borb.pdf.canvas.layout.table.fixed_column_width_table import (
    FixedColumnWidthTable as Table,
)
from borb.pdf.canvas.layout.text.paragraph import Paragraph
from borb.pdf.canvas.layout.layout_element import Alignment
from borb.pdf.canvas.layout.table.table import TableCell
from borb.pdf.canvas.layout.page_layout.multi_column_layout import MultiColumnLayout
from borb.pdf.canvas.layout.image.image import Image
from borb.pdf.canvas.color.color import HexColor, X11Color
from borb.pdf.canvas.font.simple_font.true_type_font import TrueTypeFont
import pandas as pd
from pathlib import Path
import numpy as np
from datetime import date
from decimal import Decimal

PAD: int = 2
FONT = "Helvetica"
FONT_SIZE: int = 10


# delimits text - needed to split lines when they exceed table column width
def _delimit_text(text: str, delimiter: str, n: int) -> str:

    return delimiter.join([text[i : i + n] for i in range(0, len(text), n)])


# translates text
def _translate(text: str = "", language: str = "en") -> str:

    if language == "en":
        return text

    # download/install latest packages
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == "en" and x.to_code == language, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

    # translate
    return argostranslate.translate.translate(text, "en", language)


# add company info
def _build_company_info(df: pd.DataFrame, language: str = "en") -> Table:

    InvoiceDate = df.loc[0]["InvoiceDate"]
    InvoiceNumber = df.loc[0]["InvoiceNumber"]
    DueDate = df.loc[0]["DueDate"]
    CompanyStreet = df.loc[0]["CompanyStreet"]
    CompanyRegion = df.loc[0]["CompanyRegion"]
    CompanyPhone = df.loc[0]["CompanyPhone"]
    CompanyEmail = df.loc[0]["CompanyEmail"]
    CompanyWebsite = df.loc[0]["CompanyWebsite"]

    # temp: num_rows: int = 5 - (company_email == None) - (company_website == None)
    num_rows: int = 5 - (not CompanyEmail) - (not CompanyWebsite)
    table_001 = Table(number_of_rows=num_rows, number_of_columns=3)

    table_001.add(Paragraph(_translate(CompanyStreet, language), font=FONT))

    table_001.add(
        Paragraph(
            _translate("Date:", language),
            font=FONT,
            horizontal_alignment=Alignment.RIGHT,
        )
    )
    table_001.add(
        Paragraph(
            "%d/%d/%d" % (InvoiceDate.month, InvoiceDate.day, InvoiceDate.year),
            font=FONT,
        )
    )

    table_001.add(Paragraph(_translate(CompanyRegion, language), font=FONT))
    table_001.add(
        Paragraph(
            _translate("Invoice Number:", language),
            font=FONT,
            horizontal_alignment=Alignment.RIGHT,
        )
    )
    table_001.add(Paragraph(InvoiceNumber, font=FONT))

    table_001.add(Paragraph(CompanyPhone, font=FONT))
    table_001.add(
        Paragraph(
            _translate("Due Date:", language),
            font=FONT,
            horizontal_alignment=Alignment.RIGHT,
        )
    )
    table_001.add(
        Paragraph("%d/%d/%d" % (DueDate.month, DueDate.day, DueDate.year), font=FONT)
    )

    if CompanyEmail:
        table_001.add(Paragraph(CompanyEmail, font=FONT))
        table_001.add(Paragraph(" "))
        table_001.add(Paragraph(" "))

    if CompanyWebsite:
        table_001.add(Paragraph(CompanyWebsite, font=FONT))
        table_001.add(Paragraph(" "))
        table_001.add(Paragraph(" "))

    table_001.set_padding_on_all_cells(
        Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD)
    )
    table_001.no_borders()
    return table_001


# add billing information
def _build_billing_and_shipping(df: pd.DataFrame, language: str = "en") -> Table:

    BillToName = df.loc[0]["BillToName"]
    BillToStreet = df.loc[0]["BillToStreet"]
    BillToRegion = df.loc[0]["BillToRegion"]
    BillToPhone = df.loc[0]["BillToPhone"]
    ShipToName = df.loc[0]["ShipToName"]
    ShipToStreet = df.loc[0]["ShipToStreet"]
    ShipToRegion = df.loc[0]["ShipToRegion"]
    ShipToPhone = df.loc[0]["ShipToPhone"]

    table_001 = Table(number_of_rows=5, number_of_columns=2)
    table_001.add(Paragraph(_translate("Bill To:", language), font=FONT))
    table_001.add(Paragraph(_translate("Ship To:", language), font=FONT))
    table_001.add(
        Paragraph(_translate(str(BillToName), language), font=FONT)
    )  # BILLING
    table_001.add(
        Paragraph(_translate(str(ShipToName), language), font=FONT)
    )  # SHIPPING
    table_001.add(
        Paragraph(_translate(str(BillToStreet), language), font=FONT)
    )  # BILLING
    table_001.add(
        Paragraph(_translate(str(ShipToStreet), language), font=FONT)
    )  # SHIPPING
    table_001.add(
        Paragraph(_translate(str(BillToRegion), language), font=FONT)
    )  # BILLING
    table_001.add(
        Paragraph(_translate(str(ShipToRegion), language), font=FONT)
    )  # SHIPPING
    table_001.add(Paragraph(str(BillToPhone), font=FONT))  # BILLING
    table_001.add(Paragraph(str(ShipToPhone), font=FONT))  # SHIPPING

    table_001.set_padding_on_all_cells(
        Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD)
    )
    table_001.no_borders()
    return table_001


# build itemized table
def _build_itemized(group: pd.DataFrame, language: str = "en") -> Table:

    table_001 = Table(
        number_of_rows=group.shape[0] + 2,
        number_of_columns=7,
        column_widths=[
            Decimal(4),
            Decimal(2),
            Decimal(2.5),
            Decimal(2.5),
            Decimal(2),
            Decimal(2.5),
            Decimal(2.5),
        ],
    )
    for h in [
        "Product Description",
        "Quantity",
        "Product Price",
        "Exempt",
        "Tax Rate",
        "Tax Amount",
        "Total Price",
    ]:
        table_001.add(
            TableCell(
                Paragraph(
                    _translate(h, language),
                    font=FONT,
                    font_size=FONT_SIZE,
                    font_color=X11Color("White"),
                ),
                background_color=HexColor("14396b"),
            )
        )
    odd_color = HexColor("BBBBBB")
    even_color = HexColor("FFFFFF")
    for index, row in group.iterrows():
        c = even_color if index % 2 == 0 else odd_color
        table_001.add(
            TableCell(
                Paragraph(
                    _translate(str(row["Product"]), language),
                    font=FONT,
                    font_size=FONT_SIZE,
                ),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph(
                    _translate(str(row["Quantity"]), language),
                    font=FONT,
                    font_size=FONT_SIZE,
                ),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph("$ " + str(row["UnitPrice"]), font=FONT, font_size=FONT_SIZE),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph("$ " + str(row["Exempt"]), font=FONT, font_size=FONT_SIZE),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph(
                    str(row["TaxRate"] * 100) + " %", font=FONT, font_size=FONT_SIZE
                ),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph("$ " + str(row["TaxAmount"]), font=FONT, font_size=FONT_SIZE),
                background_color=c,
            )
        )
        table_001.add(
            TableCell(
                Paragraph("$ " + str(row["Total"]), font=FONT, font_size=FONT_SIZE),
                background_color=c,
            )
        )
    table_001.add(
        TableCell(
            Paragraph(
                _translate("Total", language),
                font=FONT,
                horizontal_alignment=Alignment.RIGHT,
            ),
            column_span=6,
        )
    )
    table_001.add(
        TableCell(
            Paragraph(
                "$ " + str(group["Total"].sum()),
                font=FONT,
                horizontal_alignment=Alignment.RIGHT,
            )
        )
    )

    table_001.set_padding_on_all_cells(
        Decimal(PAD), Decimal(PAD), Decimal(0), Decimal(PAD)
    )
    return table_001


# read database
def _read_file(
    filePath: str, fileHeader: int = 0, language: str = "en"
) -> pd.DataFrame:

    extension = filePath.split(".")[-1].lower()
    if extension == "xlsx":
        df = pd.read_excel(filePath, header=fileHeader)
    elif extension == "csv":
        df = pd.read_csv(filePath, header=fileHeader)
    else:
        raise ValueError(
            f"Unsupported file format: {extension}\nSupported file formats: xlsx, csv"
        )
    return df


# fill in missing values
def _interpolate(df: pd.DataFrame) -> pd.DataFrame:

    filled_df = df

    # add missing columns
    fields = [
        "Language",
        "InvoiceDate",
        "InvoiceNumber",
        "DueDate",
        "CompanyStreet",
        "CompanyRegion",
        "CompanyPhone",
        "CompanyEmail",
        "CompanyWebsite",
        "BillToName",
        "BillToStreet",
        "BillToCity",
        "BillToRegion",
        "BillToZip",
        "BillToPhone",
        "ShipToName",
        "ShipToStreet",
        "ShipToCity",
        "ShipToRegion",
        "ShipToZip",
        "ShipToPhone",
        "Product",
        "Quantity",
        "UnitPrice",
        "Exempt",
        "TaxRate",
        "TaxAmount",
        "Total",
    ]
    for field in fields:
        if field not in filled_df.columns:
            filled_df[field] = None

    # interpolate shipping region
    filled_df["ShipToRegion"] = (
        np.where(~filled_df["ShipToCity"].isna(), filled_df["ShipToCity"] + ", ", "")
        + filled_df["ShipToCountry"]
        + np.where(~filled_df["ShipToZip"].isna(), " " + filled_df["ShipToZip"], "")
    )

    # interpolate billing region
    filled_df["BillToRegion"] = (
        np.where(~filled_df["BillToCity"].isna(), filled_df["BillToCity"] + ", ", "")
        + filled_df["BillToCountry"]
        + np.where(~filled_df["BillToZip"].isna(), " " + filled_df["BillToZip"], "")
    )

    # fill missing values with defaults
    filled_df.fillna(
        value={
            "InvoiceDate": date.today(),
            "InvoiceNumber": -1,
            "DueDate": date.today(),
            "CompanyStreet": "445 Hoes Lane",
            "CompanyRegion": "Piscataway, NJ 08854",
            "CompanyPhone": "+1 732 981 0060",
            "CompanyEmail": "society-info@ieee.org",
            "CompanyWebsite": "ieee.org",
            "BillToName": "-",
            "BillToStreet": "-",
            "BillToRegion": "-",
            "BillToZip": "-",
            "BillToPhone": "-",
            "ShipToName": "-",
            "ShipToStreet": "-",
            "ShipToRegion": "-",
            "ShipToZip": "-",
            "ShipToPhone": "-",
            "Product": "-",
            "Quantity": 1,
            "UnitPrice": 0,
            "Exempt": 0,
            "TaxRate": 0.05,
        },
        inplace=True,
    )

    # fill in missing UnitPrice, Quantity, TaxRate, TaxAmount, Exempt, or Total fields
    mask = (
        filled_df[["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Exempt", "Total"]]
        .isnull()
        .sum(axis=1)
        == 1
    )

    def _fill_missing_price(row):
        filled_row = row
        if pd.isna(row["Total"]):
            filled_row["Total"] = (
                row["UnitPrice"] * row["Quantity"] - row["Exempt"]
            ) * (1 + row["TaxRate"])
        elif pd.isna(row["TaxAmount"]):
            filled_row["TaxAmount"] = (
                row["UnitPrice"] * row["Quantity"] - row["Exempt"]
            ) * row["TaxRate"]
        elif pd.isna(row["Exempt"]):
            filled_row["Exempt"] = row["UnitPrice"] * row["Quantity"] - row["Total"] / (
                1 + row["TaxRate"]
            )
        elif pd.isna(row["Quantity"]):
            filled_row["Quantity"] = (
                row["Total"] / (1 + row["TaxRate"]) + row["Exempt"]
            ) / row["UnitPrice"]
        elif pd.isna(row["UnitPrice"]):
            filled_row["UnitPrice"] = (
                row["Total"] / (1 + row["TaxRate"]) + row["Exempt"]
            ) / row["Quantity"]
        elif pd.isna(row["TaxRate"]):
            filled_row["TaxRate"] = (
                row["Total"] / ((row["UnitPrice"] * row["Quantity"]) - row["Exempt"])
            ) - 1
        return filled_row

    filled_df.loc[
        mask, ["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Exempt", "Total"]
    ] = filled_df.loc[
        mask, ["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Exempt", "Total"]
    ].apply(
        _fill_missing_price, axis=1
    )

    return filled_df


def _create_pdf(
    df: pd.DataFrame,
    i: int,
    logo: str = "https://1000logos.net/wp-content/uploads/2019/03/IEEE-Logo.jpg",
    language: str = "en",
) -> None:

    pdf = Document()
    page = Page()
    pdf.add_page(page)

    # set page layout
    page_layout = MultiColumnLayout(
        page,
        column_widths=[page.get_page_info().get_width() - Decimal(72)],
        margin_top=Decimal(36),
        margin_right=Decimal(36),
        margin_bottom=Decimal(36),
        margin_left=Decimal(36),
    )

    # add logo
    page_layout.add(Image(logo, width=Decimal(224), height=Decimal(128)))

    # add company info
    page_layout.add(_build_company_info(df, language))

    # spacer paragraph
    page_layout.add(Paragraph(" "))

    # add billing and shipping info
    page_layout.add(_build_billing_and_shipping(df, language))

    # add itemized invoice data
    page_layout.add(_build_itemized(df, language))

    # Create [generated] folder if it doesn't exist
    generation_path = "generated"
    if not os.path.exists(generation_path):
        os.makedirs(generation_path)

    base_filename = f"Invoice_{df.loc[0]['InvoiceNumber']}{language if language != 'en' else ''}.pdf"
    # Sanitize the file_name or ensure it's safe before appending it to the path
    safe_file_name = os.path.join(generation_path, os.path.basename(base_filename))

    # write pdf
    with open( safe_file_name, "wb") as pdf_file_handle:
        PDF.dumps(pdf_file_handle, pdf)


def generate_invoice(**kwargs) -> list[str]:
    global FONT

    if "filePath" in kwargs:
        try:
            df = _read_file(**kwargs)
        except ValueError as e:
            print(e)
    else:
        df = pd.DataFrame(kwargs)

    # correct column names for this specific file "AE Sample data.xlsx" - will become more robust in the future
    try:
        df.rename(
            columns={
                "#InvoiceDate": "InvoiceDate",
                "GrossAmount": "UnitPrice",
                "TaxCollected": "TaxAmount",
                "BILL TO COUNTRY": "BillToCountry",
                "BillToAddress": "BillToStreet",
                "ShipToAddress": "ShipToStreet",
            },
            inplace=True,
        )

        languages = {
            "english": "en",
            "arabic": "ar",
            "japanese": "jp",
        }
        fonts = {
            "english": Path(__file__).parent
            / "fontpackage\\Noto_Sans\\NotoSans-VariableFont_wdth,wght.ttf",
            "arabic": Path(__file__).parent
            / "fontpackage\\Noto_Nastaliq_Urdu\\NotoNastaliqUrdu-VariableFont_wght.ttf",
            "japanese": Path(__file__).parent
            / "fontpackage\\Noto_Sans_JP\\NotoSansJP-VariableFont_wght.ttf",
        }

        df["Language"] = languages[kwargs["language"]]
        fontPath = fonts[kwargs["language"]]
        FONT = TrueTypeFont.true_type_font_from_file(fontPath)

    except KeyError as e:
        print(f"Error renaming columns: {e}")

    # interpolate missing values
    df = _interpolate(df)

    # group together invoice rows by invoice number, summing quantites for the same products
    # grouped = df.groupby(["InvoiceNumber", "Product"]).agg({"Quantity": "sum"}).groupby("InvoiceNumber")
    grouped = df.groupby("InvoiceNumber", as_index=False)

    print("Creating invoices...")

    # generate unique invoice for each group
    for i, (_, group) in enumerate(grouped):

        try:
            group = group.reset_index()
            if group.loc[0]["Language"] != "en":
                _create_pdf(group, i, language=group.loc[0]["Language"])
                print(f"Invoice {i + 1} created in {group.loc[0]['Language']}")
        except Exception as e:
            print(f"Invoice {i + 1} failed!\n{e}\n")

    print("Done!")

    return df["InvoiceNumber"].toList()



if __name__ == "__main__":
    generate_invoice(filePath="AE Sample data.xlsx", fileHeader=0, language="en")
