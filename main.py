from unstructured.partition.pdf import partition_pdf # https://docs.unstructured.io/open-source/core-functionality/partitioning#partition-pdf
from langchain_core.prompts import ChatPromptTemplate  # https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.chat.ChatPromptTemplate.html
from langchain_ollama.llms import OllamaLLM 

# High Level Process
    # Extract Content From PDF, Write to XML
    # Prompt LLM to answer specific questions about document, using document XML as content
    # Evaluate document / extracted fields for fruad
    # Perform rules-based determination to provide approval / denial, with justification

    # Quality Checks - OCR Quality Minimums, LLM Answer Confidence Scores
    # Extraction Quaility: Table Handling, Image Handling
    # Value Add Features - Show bounding box for answer sources, fraud indicators, with confidence scores

    # MVP POC: 
        # OCR Step, with confidence breakpoints
            # text
            # tables
            # handwriting
            # signature check - fraud reqs

            # field exists      
            # extract field     
        
        # Acceptable document check determination - is the document of one of the acceptable types (SSA Benefit Verification Letter, etc)

        # Extract values with LLM for rules-based determination flows - Elizabeth to identify a few rules

        # Identify some rules based flows / requirements, that we can build a simple decision outcome

        # approval / denial rationale statement 

        # fraud detection support - identify a rule or two - Elizabeth to identify a few rules

        # fraud check rationale statements

        # Goals - for review on Monday AM 4.21:
            # POC Arch / Solution Plan
            # Dev in Progress
            # Refined MVP requirements

            # Target Initial Demo for Wednesday 4.23

    # +1: PDF annotation with answer sources, fraud identifiers  
    # +1: Document resolution, format, quality checks  
    # +1: Acceptable document check determination  

# execute llm query against document xml
def llm_query(chain, question):
    resp = chain.invoke({"question": question, "xml": xml})
    print(question + ": " + resp)
    return resp

# extract pdf docoument content to xml
def pdf_to_xml(filepath):
    elements = partition_pdf(filepath, strategy="hi_res", infer_table_structure=True)

    elements_list = [element.to_dict() for element in elements]

    # write extracted content to xml
    xml_content = "<document>\n"
    for element_dict in elements_list:
        element_type = element_dict.get("type", "unknown")
        element_text = element_dict.get("text", "")
        if element_type == "Table":
            xml_content += f"  <{element_type}>{element_dict['metadata']['text_as_html']}</{element_type}>\n"
        else:
            xml_content += f"  <{element_type}>{element_text}</{element_type}>\n"
    xml_content += "</document>"

    return(xml_content)

# Setup Prompt and Model
template = """Please answer the following question based on the XML context. If the answer to the question refers to a dollar amount, respond only with the dollar amount. If the question can be answered with a 'yes' or 'no' response, respond with 'yes' or 'no' to answer the given question.  Do not make up an answer. If the question cannot be answered definitively, respond with 'Not Found'.
Question: {question}
Context: {xml}
"""

model = OllamaLLM(model="llama3:8b")
prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

# Extract Source Document to XML
#xml = pdf_to_xml("../docs/SSA Benefit Verification Letter - Acceptable.pdf")
xml = pdf_to_xml("../docs/SSA BPQY - Acceptable.pdf")
with open("out.xml", "w") as outfile:
    outfile.write(xml)

# Answer questions from doc
q1 = llm_query(chain, "What was the full monthly social security benefit before any deductions?")
q2 = llm_query(chain, "Does the document indicate the recipient is elegible for monthly disability benefits?")
q3 = llm_query(chain, "What is the date associated with this document?")
q4 = llm_query(chain, "What is the BNC number associated with this document?")
q5 = llm_query(chain, "What is the favorite food of the document recipient?")
q6 = llm_query(chain, "Is the document a social security administration benefit verification letter?")