import boto3
from enum import Enum
import time
from typing import Dict, Any, List

class FindingStatus(Enum):
    TRUE = True
    FALSE = False
    UNKNOWN = None

class Finding:
    def __init__(self, name: str, code: str, status: FindingStatus = FindingStatus.UNKNOWN, 
                 description: str = "Finding has not been evaluated yet"):
        self.name = name
        self.code = code
        self.status = status
        self.description = description

    def __str__(self):
        return f"Finding(name='{self.name}', code={self.code}, status={self.status.name}, description='{self.description}')"

    def __repr__(self):
        return self.__str__()

    def set_code(self, code: str):
        self.code = code

    def set_status(self, status: FindingStatus):
        self.status = status

    def set_description(self, description: str):
        self.description = description

class FindingContainer:
    def __init__(self):
        self.findings: List[Finding] = []

    def add_finding(self, finding: Finding):
        """
        Add a finding to the container.

        :param finding: The Finding object to add
        """
        self.findings.append(finding)

    def print_findings(self):
        """
        Print all findings in the container.
        """
        for finding in self.findings:
            print(f"Name: {finding.name}")
            print(f"Code: {finding.code}")
            print(f"Status: {finding.status.name}")
            print(f"Description: {finding.description}")
            print("-" * 30)

def analyze_document(bucket: str, document: str) -> Dict[str, Any]:
    """
    Analyze a document using AWS Textract.

    :param bucket: S3 bucket name
    :param document: S3 object key (document name)
    :return: Dictionary containing Textract analysis results
    """
    client = boto3.client('textract')
    
    response = client.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket,
                'Name': document
            }
        },
        FeatureTypes=['LAYOUT', 'TABLES', 'FORMS']
    )
    
    job_id = response['JobId']
    
    while True:
        time.sleep(10)
        result = client.get_document_analysis(JobId=job_id)
        status = result['JobStatus']
        print(status)

        if status in ['SUCCEEDED', 'FAILED']:
            break
    
    if status == 'SUCCEEDED':
        return result
    else:
        raise Exception(f"Document analysis failed: {result.get('StatusMessage', 'Unknown error')}")

def validate_document_confidence(analysis_result: Dict[str, Any], percent_of_doc, confidence_val) -> bool:
    """
    Validate document based on confidence values from Textract analysis.

    :param analysis_result: The result from Textract's get_document_analysis function
    :param percent_of_doc: The minimum percentage of the document that should meet the confidence threshold 
    :param confidence_val: The minimum confidence value to consider
    :return: Boolean indicating if the document is valid based on the specified criteria
    """
    confidence_values: List[float] = []

    # Iterate through all blocks in the document
    for block in analysis_result.get('Blocks', []):
        if 'Confidence' in block:
            confidence_values.append(block['Confidence'])

    if not confidence_values:
        return False  # No confidence values found

    # Calculate the number of blocks that meet or exceed the confidence threshold
    high_confidence_blocks = sum(1 for conf in confidence_values if conf >= confidence_val)

    # Calculate the percentage of high-confidence blocks
    percentage_high_confidence = high_confidence_blocks / len(confidence_values)

    # Validate if the percentage meets or exceeds the specified threshold
    return percentage_high_confidence >= percent_of_doc


def retrieve_handwritten_words(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve the blocks that contain handwritten words from Textract analysis.

    :param analysis_result: The result from Textract's get_document_analysis function
    :return: Dictionary containing Textract blocks that are detected as handwritten words
    """
    handwritten_blocks = [
        block for block in analysis_result['Blocks']
        if block['BlockType'] == 'WORD' and block.get('TextType') == 'HANDWRITING'
    ]
    return handwritten_blocks

print("Starting analysis...")
# Valid BPQY doc
textract_analysis = analyze_document('textract-console-us-gov-west-1-bb875f26-b19b-4e36-8053-0b819f9d', 'e25b64ab_e822_4310_869d_9e51ffca8577_ssa_bpqy___acceptable___ssdi_re_exam_cycle_3__years.pdf')

# Random doc with handwriting
# textract_analysis = analyze_document('textract-console-us-gov-west-1-bb875f26-b19b-4e36-8053-0b819f9d', 'table-with-handwriting-pdf.pdf')

# textract_analysis to be used as input for LLM

# Create a FindingContainer
findings = FindingContainer()

## Low Resolution Finding
# Determine low resolution based on confidence scores
percent_of_doc=0.5
confidence_val=90.0
is_valid = validate_document_confidence(textract_analysis, percent_of_doc, confidence_val)
if is_valid:
    # print(f"Document is valid because over {percent_of_doc*100}% of the document was detected with a confidence score of over {confidence_val}.")
    low_res_finding = Finding("Low Resolution", "OtherLowRes", FindingStatus.FALSE, f"Document is valid because over {percent_of_doc*100}% of the document was detected with a confidence score of over {confidence_val}.")
if not is_valid:
    # print(f"Document is not valid because over {percent_of_doc*100}% of the document was detected with a confidence score of under {confidence_val}.")
    low_res_finding = Finding("Low Resolution", "OtherLowRes", FindingStatus.TRUE, f"Document is not valid because over {percent_of_doc*100}% of the document was detected with a confidence score of under {confidence_val}.")
findings.add_finding(low_res_finding)

## Fraud Finding
# Determine fraud if handwriting is detected
handwritten_words = retrieve_handwritten_words(textract_analysis)
if not handwritten_words:
    # print("Document is not considered fraudulent because no handwriting detected.")
    handwritten_finding = Finding("Handwriting Present", "Fraud", FindingStatus.FALSE, "Document is not considered fraudulent because no handwriting detected.")
if handwritten_words:
    description = "Document is considered fraudulent because handwriting is detected.\n"
    description += "The following words were detected as handwriting with the corresponding confidence scores (out of 100):\n"
    for part in handwritten_words:
        # print("Document is considered fraudulent because handwriting is detected.")
        # print("The following words were detected as handwriting with the corresponding confidence scores (out of 100):")
        # print(f"Handwritten text: {part['Text']}, Confidence: {part['Confidence']}")
        description += f"Handwritten text: {part['Text']}, Confidence: {part['Confidence']}\n"
    handwritten_finding = Finding("Handwriting Present", "Fraud", FindingStatus.TRUE, description)
findings.add_finding(handwritten_finding)

# Placeholders for other findings
illegible_finding = Finding("Illegible Documents", "OtherIllegible")
findings.add_finding(illegible_finding)
doc_mismatch_finding = Finding("Applicant Info Mismatch", "DocMismatch")
findings.add_finding(doc_mismatch_finding)
irrelevant_finding = Finding("Irrelevant Documents", "OtherIrrelevant")
findings.add_finding(irrelevant_finding)
ssa_short_cycle_finding = Finding("Re-exam Cycle Less than 3 years", "SSAcyclein3yrs")
findings.add_finding(ssa_short_cycle_finding)
ssa_amrc_finding = Finding("MRC", "SSAMRC")
findings.add_finding(ssa_amrc_finding)
ssa_date_less_finding = Finding("Date Less", "SSADateLess")
findings.add_finding(ssa_date_less_finding)

# Print summary of findings
findings.print_findings()