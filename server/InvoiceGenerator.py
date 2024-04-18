import os
import argostranslate.package
import argostranslate.translate
import jinja2
import numpy as np
import pandas as pd
from datetime import date, timedelta
from weasyprint import HTML


# translates text
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

    # translate
    return argostranslate.translate.translate(text, src_language, dest_language)

def translate_wrapper(text, src_language, dest_language):
    return translate(text, src_language, dest_language)


# read database
def read_file(
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
def interpolate(df: pd.DataFrame) -> pd.DataFrame:

    filled_df = df

    if "DueDate" not in filled_df.columns:
        filled_df["DueDate"] = filled_df["InvoiceDate"] + timedelta(days=30)

    # add missing columns
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
    i: int,
    logo: str = "https://1000logos.net/wp-content/uploads/2019/03/IEEE-Logo.jpg",
    src_language: str = "en",
    dest_language: str = "en"
) -> None:

    cwd: str = os.getcwd()

    # Create [generated] folder if it doesn't exist
    generation_path = "generated"
    if not os.path.exists(generation_path):
        os.makedirs(generation_path)

    base_filename = f"Invoice_{df.loc[0]["InvoiceNumber"]}_{src_language}_to_{dest_language}.pdf"
    safe_filename = os.path.join(cwd, generation_path, os.path.basename(base_filename))

    # write pdf
    row1 = df.loc[0]
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
                                  total=df["Total"].sum())


    with open(safe_filename, "wb") as pdf_file:
        HTML(string=html_output, base_url="https://fonts.googleapis.com").write_pdf(pdf_file)


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
            create_pdf(group, i, src_language=src_language, dest_language=dest_language)
            print(f"Invoice {i + 1}, # {group.loc[0]["InvoiceNumber"]} created, translating from {src_language} to {dest_language}")
        except Exception as e:
            print(f"Invoice {i + 1}, # {group.loc[0]["InvoiceNumber"]}, failed!\n{e}\n")
    print("Done!")

    return df["InvoiceNumber"].to_list()


if __name__ == "__main__":
    generate_invoice(filePath="AE Sample data.xlsx", fileHeader=0, src_language="en", dest_language="ja")
