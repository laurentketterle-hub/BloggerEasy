import re
def markdown_to_html(md_text):
    html=md_text
    html=re.sub(r"### (.+)",r"<h3></h3>",html)
    html=re.sub(r"## (.+)",r"<h2></h2>",html)
    html=re.sub(r"# (.+)",r"<h1></h1>",html)
    html=re.sub(r"\*\*(.+?)\*\*",r"<strong></strong>",html)
    html=re.sub(r"\*(.+?)\*",r"<em></em>",html)
    html=re.sub(r"\[(.+?)\]\((.+?)\)",r"<a href=""></a>",html)
    html=re.sub(r"- (.+)",r"<li></li>",html)
    html=re.sub(r"

","</p><p>",html)
    return f"<p>{html}</p>"
