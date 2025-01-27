import PyPDF2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure
import pdfplumber
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
import os

# function to extract text from a PDF element
def text_extraction(element):
    line_text = element.get_text()
    line_formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            for character in text_line:
                if isinstance(character, LTChar):
                    line_formats.append(character.fontname)
                    line_formats.append(character.size)
    format_per_line = list(set(line_formats))
    return (line_text, format_per_line)

# function to extract tables from a PDF page
def extract_table(pdf_path, page_num, table_num):
    pdf = pdfplumber.open(pdf_path)
    table_page = pdf.pages[page_num]
    table = table_page.extract_tables()[table_num]
    return table

# function to convert a table into string format
def table_converter(table):
    table_string = '<table border="1">'
    for row in table:
        table_string += '<tr>'
        for item in row:
            cleaned_item = item.replace('\n', ' ') if item and '\n' in item else 'None' if not item else item
            table_string += f'<td>{cleaned_item}</td>'
        table_string += '</tr>'
    table_string += '</table>'
    return table_string

# check if an element is inside any table
def is_element_inside_any_table(element, page, tables):
    x0, y0up, x1, y1up = element.bbox
    y0 = page.bbox[3] - y1up
    y1 = page.bbox[3] - y0up
    for table in tables:
        tx0, ty0, tx1, ty1 = table.bbox
        if tx0 <= x0 <= x1 <= tx1 and ty0 <= y0 <= y1 <= ty1:
            return True
    return False

# find the table corresponding to an element
def find_table_for_element(element, page, tables):
    x0, y0up, x1, y1up = element.bbox
    y0 = page.bbox[3] - y1up
    y1 = page.bbox[3] - y0up
    for i, table in enumerate(tables):
        tx0, ty0, tx1, ty1 = table.bbox
        if tx0 <= x0 <= x1 <= tx1 and ty0 <= y0 <= y1 <= ty1:
            return i
    return None

def crop_image(element, pageObj):
    # get the coordinates to crop the image from PDF
    [image_left, image_top, image_right, image_bottom] = [element.x0,element.y0,element.x1,element.y1] 
    pageObj.mediabox.lower_left = (image_left, image_bottom)
    pageObj.mediabox.upper_right = (image_right, image_top)
    cropped_pdf_writer = PyPDF2.PdfWriter()
    cropped_pdf_writer.add_page(pageObj)
    # save the cropped PDF to a new file
    with open('cropped_image.pdf', 'wb') as cropped_pdf_file:
        cropped_pdf_writer.write(cropped_pdf_file)

# create a function to convert the PDF to images
def convert_to_images(input_file,):
    images = convert_from_path(input_file)
    image = images[0]
    output_file = 'PDF_image.png'
    image.save(output_file, 'PNG')

# create a function to read text from images
def image_to_text(image_path):
    img = Image.open(image_path)
    # Extract the text from the image
    text = pytesseract.image_to_string(img)
    return text

# Function to generate HTML content from extracted data
def generate_html(page_num, page_text, page_tables, page_images):
    html_content = f'<html><head><title>Page {page_num + 1}</title></head><body>'
    html_content += f'<h1>Page {page_num + 1}</h1>'
    
    # Add text content
    html_content += '<h2>Text Content:</h2><p>'
    html_content += '<br>'.join(page_text)
    html_content += '</p>'
    
    # Add tables
    html_content += '<h2>Tables:</h2>'
    html_content += ''.join(page_tables)
    
    # Add images with extracted text (if available)
    if page_images:
        html_content += '<h2>Images:</h2>'
        for image_text in page_images:
            html_content += f'<p>Extracted text from image: <br>{image_text}</p>'
        html_content += f'<img src="PDF_image.png" alt="Extracted Image"><br>'
    
    html_content += '</body></html>'
    return html_content

# Main function to process a PDF and save the result as an HTML file
def process_pdf(pdf_path, output_html_path):
    pdfFileObj = open(pdf_path, 'rb')
    pdfReaded = PyPDF2.PdfReader(pdfFileObj)
    html_content = ''
    image_flag = False

    for pagenum, page in enumerate(extract_pages(pdf_path)):
        pageObj = pdfReaded.pages[pagenum]
        page_text = []
        page_tables = []
        page_images = []

        pdf = pdfplumber.open(pdf_path)
        page_tables_data = pdf.pages[pagenum]
        tables = page_tables_data.find_tables()
        if tables:
            for table_num in range(len(tables)):
                table = extract_table(pdf_path, pagenum, table_num)
                table_string = table_converter(table)
                page_tables.append(table_string)

        page_elements = [(element.y1, element) for element in page._objs]
        page_elements.sort(key=lambda a: a[0], reverse=True)

        for component in page_elements:
            element = component[1]
            if not is_element_inside_any_table(element, page, tables):
                if isinstance(element, LTTextContainer):
                    (line_text, format_per_line) = text_extraction(element)
                    page_text.append(line_text)

                if isinstance(element, LTFigure):
                    crop_image(element, pageObj)
                    convert_to_images('cropped_image.pdf')
                    image_text = image_to_text('PDF_image.png')
                    page_images.append(image_text)
                    image_flag = True

        html_content += generate_html(pagenum, page_text, page_tables, page_images)

    pdfFileObj.close()

    with open(output_html_path, 'w') as output_file:
        output_file.write(html_content)

pdf_path = 'test1.pdf' #change the file as per requirement
output_html_path = 'output.html'
process_pdf(pdf_path, output_html_path)
print(f"PDF content has been extracted and saved to {output_html_path}")
