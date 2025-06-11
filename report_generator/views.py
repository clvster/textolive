from django.shortcuts import render, redirect
from django.conf import settings
from django.http import FileResponse
import os
import subprocess
import uuid
import logging

logger = logging.getLogger(__name__)

def latex_escape(text):
    replacements = {
        '_': r'\_',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '{': r'\{',
        '}': r'\}',
        '\\': r'\textbackslash{}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}'
    }
    if not isinstance(text, str):
        text = str(text)
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Заменяем \n\n на \par для начала нового абзаца
    text = text.replace('\n\n', '\n\\par\n')
    # Заменяем одиночные \n на пробел
    text = text.replace('\n', ' ')
    return text

def main(request):
    return render(request, 'main.html')

def page1(request):
    if request.method == 'POST':
        request.session['report_number'] = request.POST.get('report_number', '')
        request.session['discipline'] = request.POST.get('discipline', '')
        request.session['report_title'] = request.POST.get('report_title', '')
        request.session['by_group'] = request.POST.get('by_group', '')
        request.session['by_name'] = request.POST.get('by_name', '')
        logger.debug(f"Page1 session after POST: {request.session.items()}")
        return redirect('page2')
    return render(request, 'page1.html')

def page2(request):
    if request.method == 'POST':
        request.session['objective'] = request.POST.get('objective', '')
        request.session['task'] = request.POST.get('task', '')
        request.session['progress'] = request.POST.get('progress', '')
        logger.debug(f"Page2 session after POST: {request.session.items()}")
        return redirect('page3')
    return render(request, 'page2.html')

def page3(request):
    if request.method == 'POST':
        request.session['conclusions'] = request.POST.get('conclusions', '')
        request.session['appendix_link'] = request.POST.get('appendix_link', '')
        logger.debug(f"Page3 session before PDF generation: {request.session.items()}")

        # Загрузка TeX-шаблона
        tex_template_path = os.path.join(settings.BASE_DIR, 'report_generator', 'templates', 'report.tex')
        with open(tex_template_path, encoding='utf-8') as f:
            tex_template = f.read()

        # Экранирование и замена плейсхолдеров
        replacements = {
            'REPORT_NUMBER': request.session.get('report_number', ''),
            'DISCIPLINE': request.session.get('discipline', ''),
            'REPORT_TITLE': request.session.get('report_title', ''),
            'BY_GROUP': request.session.get('by_group', ''),
            'BY_NAME': request.session.get('by_name', ''),
            'OBJECTIVE': request.session.get('objective', ''),
            'TASK': request.session.get('task', ''),
            'PROGRESS': request.session.get('progress', ''),
            'CONCLUSIONS': request.session.get('conclusions', ''),
            'APPENDIX_LINK': request.session.get('appendix_link', '')
        }
        for key, value in replacements.items():
            tex_template = tex_template.replace(key, latex_escape(value))

        # Сохранение TeX-файла
        unique_id = str(uuid.uuid4())
        tex_filename = f"report_{unique_id}.tex"
        pdf_filename = f"report_{unique_id}.pdf"
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        tex_path = os.path.join(reports_dir, tex_filename)
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(tex_template)

        # Генерация PDF
        try:
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', reports_dir, tex_path],
                capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"PDF generation error: {e.stderr}")
            return render(request, 'error.html', {
                'error': 'Не удалось сгенерировать PDF из-за ошибок LaTeX',
                'log': e.stderr
            })

        pdf_path = os.path.join(reports_dir, pdf_filename)
        if os.path.exists(pdf_path):
            return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename='report.pdf')
        else:
            logger.error("PDF file not found after generation")
            return render(request, 'error.html', {
                'error': 'PDF-файл не был создан',
                'log': 'Файл PDF не найден после попытки генерации'
            })

    return render(request, 'page3.html')