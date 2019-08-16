# The MIT License (MIT)
#
# Copyright (c) 2015 University of East Anglia, Norwich, UK
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Developed by Geoffrey French in collaboration with Dr. M. Fisher and
# Dr. M. Mackiewicz.

def flask_labeller(labelled_images, label_classes, config=None, use_reloader=True, debug=True):
    import json
    import flask

    from flask import Flask, render_template, request, make_response, send_from_directory
    import flask_login

    try:
        from flask_socketio import SocketIO, emit as socketio_emit
    except ImportError:
        SocketIO = None
        socketio_emit = None

    from image_labelling_tool import labelling_tool

    # Generate image IDs list
    image_ids = [str(i)   for i in range(len(labelled_images))]
    # Generate images table mapping image ID to image so we can get an image by ID
    images_table = {image_id: img   for image_id, img in zip(image_ids, labelled_images)}
    # Generate image descriptors list to hand over to the labelling tool
    # Each descriptor provides the image ID, the URL and the size
    image_descriptors = []
    for image_id, img in zip(image_ids, labelled_images):
        height, width = img.image_size
        image_descriptors.append(labelling_tool.image_descriptor(
            image_id=image_id, url='/image/{}'.format(image_id),
            width=width, height=height
        ))


    app = Flask(__name__, static_folder='static')
    app.secret_key = 'super secret string'

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)


    users = {
        'vaishak@atkinsglobal.com': {'password': 'secret'},
        'abhishek@atkinsglobal.com': {'password': 'secret'},
        'janpreet@atkinsglobal.com': {'password': 'secret'},
        'shril@atkinsglobal.com': {'password': 'secret'}
    }


    class User(flask_login.UserMixin):
        pass


    @login_manager.user_loader
    def user_loader(email):
        if email not in users:
            return

        user = User()
        user.id = email
        return user


    @login_manager.request_loader
    def request_loader(request):
        email = request.form.get('email')
        if email not in users:
            return

        user = User()
        user.id = email

        # DO NOT ever store passwords in plaintext and always compare password
        # hashes using constant-time comparison!
        user.is_authenticated = request.form['password'] == users[email]['password']
        return user


    if SocketIO is not None:
        print('Using web sockets')
        socketio = SocketIO(app)
    else:
        socketio = None


    if config is None:
        config = {
            'tools': {
                'imageSelector': True,
                'labelClassSelector': True,
                'labelClassFilterInitial': None,
                'drawPolyLabel': True,
                'compositeLabel': True,
                'deleteLabel': True,
                'deleteConfig': {
                    'typePermissions': {
                        'point': True,
                        'box': True,
                        'polygon': True,
                        'composite': True,
                        'group': True,
                    }
                }
            }
        }


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if flask.request.method == 'GET':
            return render_template('login.html')

        email = flask.request.form['email']

        if email not in users:
            return render_template('login.html')

        if flask.request.form['password'] == users[email]['password']:
            user = User()
            user.id = email
            flask_login.login_user(user)
            return flask.redirect(flask.url_for('index'))
        else:
            return render_template('login.html')


    @app.route('/logout')
    def logout():
        flask_login.logout_user()
        return render_template('login.html')


    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return render_template('login.html')


    @app.route('/')
    @flask_login.login_required
    def index():
        label_classes_json = [(cls.to_json() if isinstance(cls, labelling_tool.LabelClassGroup) else cls)
                               for cls in label_classes]
        return render_template('labeller_page.jinja2',
                               tool_js_urls=labelling_tool.js_file_urls('/static/labelling_tool/'),
                               label_classes=json.dumps(label_classes_json),
                               image_descriptors=json.dumps(image_descriptors),
                               initial_image_index=0,
                               config=json.dumps(config),
                               use_websockets=socketio is not None)


    if socketio is not None:
        @socketio.on('get_labels')
        def handle_get_labels(arg_js):
            image_id = arg_js['image_id']

            image = images_table[image_id]

            labels, complete = image.get_label_data_for_tool()

            label_header = dict(labels=labels,
                                image_id=image_id,
                                complete=complete)

            socketio_emit('get_labels_reply', label_header)


        @socketio.on('set_labels')
        def handle_set_labels(arg_js):
            label_header = arg_js['label_header']

            image_id = label_header['image_id']

            image = images_table[image_id]

            image.set_label_data_from_tool(label_header['labels'], label_header['complete'])

            socketio_emit('set_labels_reply', '')


    else:
        @app.route('/labelling/get_labels/<image_id>')
        @flask_login.login_required
        def get_labels(image_id):
            image = images_table[image_id]

            labels = image.labels_json
            complete = False


            label_header = {
                'labels': labels,
                'image_id': image_id,
                'complete': complete
            }

            r = make_response(json.dumps(label_header))
            r.mimetype = 'application/json'
            return r


        @app.route('/labelling/set_labels', methods=['POST'])
        @flask_login.login_required
        def set_labels():
            label_header = json.loads(request.form['labels'])
            image_id = label_header['image_id']
            complete = label_header['complete']
            labels = label_header['labels']

            image = images_table[image_id]
            image.labels_json = labels

            return make_response('')


    @app.route('/image/<image_id>')
    @flask_login.login_required
    def get_image(image_id):
        image = images_table[image_id]
        data, mimetype, width, height = image.data_and_mime_type_and_size()
        r = make_response(data)
        r.mimetype = mimetype
        return r



    @app.route('/ext_static/<path:filename>')
    @flask_login.login_required
    def base_static(filename):
        return send_from_directory(app.root_path + '/../ext_static/', filename)


    if socketio is not None:
        socketio.run(app, debug=debug, use_reloader=use_reloader)
    else:
        app.run(debug=debug, use_reloader=use_reloader)

