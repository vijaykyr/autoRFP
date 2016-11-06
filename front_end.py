import os
import webapp2
import jinja2
from document_search import get_answers

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
    
class MainPage(webapp2.RequestHandler):
    def get(self):
        template_values = {
            'answers': ["asdfsda","bbbbbbf"],
        }
        
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))
    
    def post(self):
        questions = self.request.get('questions').splitlines()
        print(type(questions))
        print(questions)
        answers = get_answers(questions)
        print(answers)
        #query_params = {'question': question}
        #self.redirect('/?' + urllib.urlencode(query_params))

#Define Routes
app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)

if __name__ == '__main__':
  #run locally (as opposed to in app engine)
  from paste import httpserver
  httpserver.serve(app, host='127.0.0.1', port='8080')
