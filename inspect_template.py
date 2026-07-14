from app import app
from flask import render_template

print('root_path:', app.root_path)
print('template_folder:', app.template_folder)
print('static_folder:', app.static_folder)

with app.test_request_context('/'):
    source, filename, uptodate = app.jinja_loader.get_source(app.jinja_env, 'index.html')
    print('filename:', filename)
    print('source snippet:', source[:200])
    html = render_template('index.html')
    print('rendered length:', len(html))
    print('rendered preview:', html[:200])
