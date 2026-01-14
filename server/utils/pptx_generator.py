from pptx import Presentation
def generate_pptx(out_path, slides_text):
    prs = Presentation()
    prs.save(out_path)
