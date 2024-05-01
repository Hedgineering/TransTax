import os
import argostranslate.package
import argostranslate.translate
import jinja2
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date, timedelta
from functools import cache
from time import perf_counter
from weasyprint import HTML

form = {}
symbol = {
    "AED": ["Emirati Dirham", "د.إ", "l"],
    "AUD": ["Australian Dollar", "$", "l"],
    "CAD": ["Canadian Dollar", "$", "l"],
    "CNY": ["Chinese Yuan Renminbi","¥", "l"],
    "EUR": ["Euro", "€", "l"],
    "GBP": ["British Pound", "£", "l"],
    "INR": ["Indian Rupee", "₹", "l"],
    "JPY": ["Japanese Yen", "¥", "l"],
    "MXN": ["Mexican Peso", "$", "l"],
    "RUB": ["Russian Ruble", "₽", "l"],
    "USD": ["US Dollar", "$", "l"],
    "WON": ["South Korean Won", "₩", "l"],
}
fields = [
    "InvoiceDate",
    "InvoiceNumber",
    "DueDate",
    "CompanyName",
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
    "TaxRate",
    "TaxAmount",
    "Total"
]

# translates text
@cache
def translate(text: str = "", src_language: str = "en", dest_language: str = "en") -> str:

    if src_language == dest_language:
        return text

    # download/install latest packages
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == src_language and x.to_code == dest_language, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

    # translate using Argos Translate
    return argostranslate.translate.translate(text, src_language, dest_language)



# converts currency
def convert_currency(amount: float, src_currency: str, dest_currency: str, date: date=date.today()-timedelta(days=1)) -> str:   
    url = "https://www.x-rates.com/historical/?from=" + src_currency + "&amount=" + str(amount) + "&date=" + str(date)
    response = requests.get(url)
    print("got response")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        extracted_text = soup.get_text()
        lines = extracted_text.split("\n")
        try:
            ind = lines.index(symbol[dest_currency][0])
            converted_amount = f"{float(lines[ind + 1]):,.2f}"
        except Exception as e:
            return -1

    if symbol[dest_currency][2] == "l":
        return symbol[dest_currency][1] + " " + str(converted_amount)
    return str(converted_amount) + " " + symbol[dest_currency][1]


# read database
def read_file(
    filePath: str, fileHeader: int = 0, language: str = "en"
) -> pd.DataFrame:

    extension = filePath.split(".")[-1].lower()
    column_type = {
        0: 'datetime64[ns]',  # Datetime
        1: 'object',           # Object (string)
        2: 'object',           # Object (string)
        3: 'object',           # Object (string)
        4: 'object',           # Object (string)
        5: 'object',           # Object (string)
        6: 'object',           # Object (string)
        7: 'float64',          # Float
        8: 'float64',          # Float
        9: 'int64',            # Integer
        10: 'int64',           # Integer
        11: 'object',          # Object (string)
        12: 'object',          # Object (string)
        13: 'object',          # Object (string)
        14: 'int64',           # Integer
        15: 'object'           # Object (string)
    }
    if extension == "xlsx":
        df = pd.read_excel(filePath, header=fileHeader, dtype=column_type)
    elif extension == "csv":
        df = pd.read_csv(filePath, header=fileHeader, dtype=column_type)
    else:
        raise ValueError(
            f"Unsupported file format: {extension}\nSupported file formats: xlsx, csv"
        )
    return df


# fill in missing values
def interpolate(df: pd.DataFrame) -> pd.DataFrame:

    filled_df = df

    if "DueDate" not in filled_df.columns:
        filled_df["DueDate"] = filled_df["InvoiceDate"] + timedelta(days=30)

    # add missing columns

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
            "DueDate": date.today() + timedelta(days=30),
            "CompanyName": "IEEE",
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
            "TaxRate": 0.05,
        },
        inplace=True,
    )

    # fill in missing UnitPrice, Quantity, TaxRate, TaxAmount, Exempt, or Total fields
    mask = (
        filled_df[["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Total"]]
        .isnull()
        .sum(axis=1)
        == 1
    )
    def fill_missing_price(row):
        filled_row = row
        if pd.isna(row["Total"]):
            filled_row["Total"] = row["UnitPrice"] * row["Quantity"] * (1 + row["TaxRate"])
        elif pd.isna(row["TaxAmount"]):
            filled_row["TaxAmount"] = row["UnitPrice"] * row["Quantity"] * row["TaxRate"]
        elif pd.isna(row["TaxRate"]):
            filled_row["TaxRate"] = (row["Total"] / ((row["UnitPrice"] * row["Quantity"]))) - 1
        elif pd.isna(row["Quantity"]):
            filled_row["Quantity"] = row["Total"] / ((1 + row["TaxRate"]) * row["UnitPrice"])
        elif pd.isna(row["UnitPrice"]):
            filled_row["UnitPrice"] = row["Total"] / ((1 + row["TaxRate"]) * row["Quantity"])
        return filled_row
    filled_df.loc[
        mask, ["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Total"]
    ] = filled_df.loc[
        mask, ["UnitPrice", "Quantity", "TaxRate", "TaxAmount", "Total"]
    ].apply(
        fill_missing_price, axis=1
    )

    return filled_df


def create_pdf(
    df: pd.DataFrame,
    src_language: str = "en",
    dest_language: str = "en",
    src_currency: str = "USD",
    dest_currency: str = "USD",
) -> None:

    cwd: str = os.getcwd()

    # Create [generated] folder if it doesn't exist
    generation_path = "generated"
    if not os.path.exists(generation_path):
        os.makedirs(generation_path)

    base_filename = f"Invoice_{df.loc[0]["InvoiceNumber"]}_{src_language}_to_{dest_language}.pdf"
    safe_filename = os.path.join(cwd, generation_path, os.path.basename(base_filename))

    # total = df["Total"].sum()
    mySum = df["Total"].sum()
    total = convert_currency(mySum, src_currency, dest_currency)

    df["UnitPrice"] = df["UnitPrice"].apply(convert_currency, args=(src_currency, dest_currency))
    df["Total"] = df["Total"].apply(convert_currency, args=(src_currency, dest_currency))
    


    # write pdf
    row1 = df.loc[0]

    """
    form = {}
    form["InvoiceDate"] = translate("Invoice Date:", "en", dest_language)
    form["InvoiceNumber"] = translate("Invoice Number:", "en", dest_language)
    form["Quantity"] = translate("Quantity", "en", dest_language)
    form["Description"] = translate("Description", "en", dest_language)
    form["UnitPrice"] = translate("Unit Price", "en", dest_language)
    form["TaxRate"] = translate("Tax Rate", "en", dest_language)
    form["Subtotal"] = translate("Subtotal", "en", dest_language)
    form["PaymentInfo"] = translate("Payment Information", "en", dest_language)
    form["DueDate"] = translate("Due Date", "en", dest_language)
    form["TotalDue"] = translate("Total Due", "en", dest_language)
    form["AccountNumber"] = translate("Account Number", "en", dest_language)
    form["RoutingNumber"] = translate("Routing Number", "en", dest_language)
    """
    t0 = perf_counter()
    form = {
        "InvoiceDate": translate("Invoice Date:", "en", dest_language),
        "InvoiceNumber": translate("Invoice Number:", "en", dest_language),
        "Quantity": translate("Quantity", "en", dest_language),
        "Description": translate("Description", "en", dest_language),
        "UnitPrice": translate("Unit Price", "en", dest_language),
        "TaxRate": translate("Tax Rate", "en", dest_language),
        "Subtotal": translate("Subtotal", "en", dest_language),
        "PaymentInfo": translate("Payment Information", "en", dest_language),
        "DueDate": translate("Due Date", "en", dest_language),
        "TotalDue": translate("Total Due", "en", dest_language),
        "AccountNumber": translate("Account Number", "en", dest_language),
        "RoutingNumber": translate("Routing Number", "en", dest_language),
    }
    invoice_info = {
        "InvoiceDate": row1["InvoiceDate"],
        "InvoiceNumber": row1["InvoiceNumber"],
        "DueDate": row1["DueDate"]
    }
    company_info = {
        "CompanyName": translate(row1["CompanyName"], src_language, dest_language),
        "CompanyStreet": translate(row1["CompanyStreet"], src_language, dest_language),
        "CompanyRegion": translate(row1["CompanyRegion"], src_language, dest_language),
        "CompanyPhone": row1["CompanyPhone"],
        "CompanyEmail": row1["CompanyEmail"],
        "CompanyWebsite": row1["CompanyWebsite"]
    }
    billing_info = {
        "BillToName": translate(row1["BillToName"], src_language, dest_language),
        "BillToStreet": translate(row1["BillToStreet"], src_language, dest_language),
        "BillToCity": row1["BillToCity"],
        "BillToRegion": row1["BillToRegion"],
        "BillToZip": row1["BillToZip"],
        "BillToPhone": row1["BillToPhone"]
    }
    shipping_info = {
        "ShipToName": translate(row1["ShipToName"], src_language, dest_language),
        "ShipToStreet": translate(row1["ShipToStreet"], src_language, dest_language),
        "ShipToCity": row1["ShipToCity"],
        "ShipToRegion": row1["ShipToRegion"],
        "ShipToZip": row1["ShipToZip"],
        "ShipToPhone": row1["ShipToPhone"]
    }
    t1 = perf_counter()

    # form = {
    #     "InvoiceDate": "Invoice Date:",
    #     "InvoiceNumber": "Invoice Number:",
    #     "Quantity": "Quantity", 
    #     "Description": "Description",
    #     "UnitPrice": "Unit Price",
    #     "TaxRate": "Tax Rate",
    #     "Subtotal": "Subtotal",
    #     "PaymentInfo": "Payment Information",
    #     "DueDate": "Due Date",
    #     "TotalDue": "Total Due",
    #     "AccountNumber": "Account Number",
    #     "RoutingNumber": "Routing Number"
    # }
    # invoice_info = {
    #     "InvoiceDate": row1["InvoiceDate"],
    #     "InvoiceNumber": row1["InvoiceNumber"],
    #     "DueDate": row1["DueDate"]
    # }
    # company_info = {
    #     "CompanyName": row1["CompanyName"],
    #     "CompanyStreet": row1["CompanyStreet"],
    #     "CompanyRegion": row1["CompanyRegion"], 
    #     "CompanyPhone": row1["CompanyPhone"],
    #     "CompanyEmail": row1["CompanyEmail"],
    #     "CompanyWebsite": row1["CompanyWebsite"]
    # }
    # billing_info = {
    #     "BillToName": row1["BillToName"],
    #     "BillToStreet": row1["BillToStreet"],
    #     "BillToCity": row1["BillToCity"],
    #     "BillToRegion": row1["BillToRegion"],
    #     "BillToZip": row1["BillToZip"],
    #     "BillToPhone": row1["BillToPhone"]
    # }
    # shipping_info = {
    #     "ShipToName": row1["ShipToName"],
    #     "ShipToStreet": row1["ShipToStreet"], 
    #     "ShipToCity": row1["ShipToCity"],
    #     "ShipToRegion": row1["ShipToRegion"],
    #     "ShipToZip": row1["ShipToZip"],
    #     "ShipToPhone": row1["ShipToPhone"]
    # }
    # from multiprocessing import Pool
    # with Pool() as pool:
    #     row1 = df.loc[0]
    #     form = {k: pool.apply(translate_wrapper, args=(v, "en", dest_language)) for k, v in form.items()}
    #     company_info = {k: pool.apply(translate_wrapper, args=(v, src_language, dest_language)) if isinstance(v, str) else v for k, v in company_info.items()}
    #     billing_info = {k: pool.apply(translate_wrapper, args=(v, src_language, dest_language)) if isinstance(v, str) else v for k, v in billing_info.items()}
    #     shipping_info = {k: pool.apply(translate_wrapper, args=(v, src_language, dest_language)) if isinstance(v, str) else v for k, v in shipping_info.items()}


    product_info = df.to_dict(orient="records")

    template_loader = jinja2.FileSystemLoader("./")
    template_env = jinja2.Environment(loader=template_loader)

    html_template = "invoice_template.html"
    template = template_env.get_template(html_template)

    html_output = template.render(form=form,
                                  invoice_info=invoice_info, 
                                  company_info=company_info, 
                                  billing_info=billing_info, 
                                  shipping_info=shipping_info, 
                                  product_info=product_info,
                                  total=total)

    t2 = perf_counter()

    with open(safe_filename, "wb") as pdf_file:
        HTML(string=html_output, base_url="https://fonts.googleapis.com").write_pdf(pdf_file)

    t3 = perf_counter()

    print(f"Total time: {t3 - t0}")
    print(f"Translation time: {t1 - t0}")
    print(f"Template render time: {t2 - t1}")
    print(f"PDF generation time: {t3 - t2}")

def generate_invoice(**kwargs) -> list[str]:
    if "filePath" in kwargs:
        try:
            df = read_file(kwargs["filePath"])
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
    except KeyError as e:
        print(f"Error renaming columns: {e}")

    # set language values
    if "src_language" in kwargs:
        src_language: str = kwargs["src_language"]
    else:
        src_language: str = "en"
    if "dest_language" in kwargs:
        dest_language: str = kwargs["dest_language"]
    else:
        dest_language: str = "en"
    if "src_currency" in kwargs:
        src_currency: str = kwargs["src_currency"]
    else:
        src_currency: str = "USD"
    if "dest_currency" in kwargs:
        dest_currency: str = kwargs["dest_currency"]
    else:
        dest_currency: str = "USD"

    # interpolate missing values
    df = interpolate(df)

    # group together invoice rows by invoice number, summing quantites for the same products
    # grouped = df.groupby(["InvoiceNumber", "Product"]).agg({"Quantity": "sum"}).groupby("InvoiceNumber")
    grouped = df.groupby("InvoiceNumber", as_index=False)

    # generate unique invoice for each group
    print("\nCreating invoices...\n")

    # with multiprocessing.Pool(processes=4) as pool:
    #     data = [(group, i, src_language, dest_language) for i, (_, group) in enumerate(grouped)]
    #     pool.starmap(create_pdf_wrapper, data)
    # print("Done!")

    for i, (_, group) in enumerate(grouped):
        try:
            group = group.reset_index()
            create_pdf(group, src_language=src_language, dest_language=dest_language, src_currency=src_currency, dest_currency=dest_currency)
            print(f"Invoice {i + 1}, # {group.loc[0]["InvoiceNumber"]} created, translating from {src_language} to {dest_language}")
        except Exception as e:
            print(f"Invoice {i + 1}, # {group.loc[0]["InvoiceNumber"]}, failed!\n{e}\n")
    print("Done!")

    return [f"Invoice_{i}_{src_language}_to_{dest_language}.pdf" for i in df["InvoiceNumber"].unique().tolist()]


if __name__ == "__main__":
    generate_invoice(filePath="AE Sample data.xlsx", fileHeader=0, src_language="en", dest_language="ja", src_currency="USD", dest_currency="JPY")
