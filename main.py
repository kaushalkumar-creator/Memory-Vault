import os
import shutil
import webbrowser
from datetime import datetime

from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import platform

from db import Database

# Hindi (Devanagari) text दिखाने के लिए font: file मौजूद हो तभी इस्तेमाल होगी
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'assets', 'fonts', 'NotoSansDevanagari-Regular.ttf')
if os.path.exists(FONT_PATH):
    LabelBase.register(name='Roboto', fn_regular=FONT_PATH, fn_bold=FONT_PATH)

Window.softinput_mode = 'below_target'

BG = (0.97, 0.97, 0.97, 1)
TEXT = (0.12, 0.12, 0.12, 1)
MUTED = (0.45, 0.45, 0.45, 1)
ACCENT = (0.20, 0.36, 0.52, 1)
LIGHT = (0.90, 0.90, 0.90, 1)
WHITE = (1, 1, 1, 1)
ERROR = (0.75, 0.20, 0.20, 1)

NAV = [('home', 'Home'), ('library', 'Library'),
       ('saved', 'Saved'), ('profile', 'Profile')]
SECTIONS = [('prompt', 'Prompts'), ('image', 'Images'),
            ('video', 'Videos'), ('event', 'Events')]
KIND_NAME = {'prompt': 'Prompt', 'video': 'Video', 'image': 'Image', 'event': 'Event'}
BODY_HINT = {
    'prompt': 'Paste your prompt here',
    'video': 'Why did you save this video?',
    'image': 'Why / where was this photo taken?',
    'event': 'Description',
}

Builder.load_string('''
<Card>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: dp(12)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<Fab>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    font_size: sp(30)
    size_hint: None, None
    size: dp(56), dp(56)
    canvas.before:
        Color:
            rgba: 0.20, 0.36, 0.52, 1
        Ellipse:
            pos: self.pos
            size: self.size
''')


class Card(BoxLayout):
    pass


class Fab(Button):
    pass


# ---------- छोटे helper functions ----------

def lbl(text, size=14, color=TEXT, bold=False):
    l = Label(text=text, font_size=sp(size), color=color, bold=bold,
              halign='left', valign='top', size_hint_y=None)
    l.bind(width=lambda w, v: setattr(w, 'text_size', (v, None)))
    l.bind(texture_size=lambda w, v: setattr(w, 'height', v[1]))
    return l


def btn(text, cb=None, primary=False, height=40):
    b = Button(text=text, size_hint_y=None, height=dp(height), font_size=sp(14),
               background_normal='', background_down='',
               background_color=ACCENT if primary else LIGHT,
               color=WHITE if primary else TEXT)
    if cb:
        b.bind(on_release=cb)
    return b


def field(hint, multiline=False, height=44, text='', bg=(0.95, 0.95, 0.95, 1)):
    return TextInput(hint_text=hint, text=text, multiline=multiline,
                     size_hint_y=None, height=dp(height), font_size=sp(15),
                     background_normal='', background_active='',
                     background_color=bg, foreground_color=TEXT,
                     hint_text_color=MUTED, cursor_color=ACCENT,
                     padding=[dp(10), dp(12)])


def make_popup(title, content, size=(0.95, 0.9)):
    return Popup(title=title, content=content, size_hint=size,
                 background='', background_color=WHITE, title_color=TEXT,
                 separator_color=ACCENT, auto_dismiss=False)


def fmt_dt(iso):
    try:
        return datetime.fromisoformat(iso).strftime('%d %b %Y, %A, %I:%M %p')
    except ValueError:
        return iso


def iso_to_dmy(iso):
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%d-%m-%Y')
    except ValueError:
        return ''


def dmy_to_iso(text):
    text = text.strip().replace('/', '-').replace('.', '-')
    return datetime.strptime(text, '%d-%m-%Y').strftime('%Y-%m-%d')


def style_tab(widget, state):
    widget.background_color = ACCENT if state == 'down' else LIGHT
    widget.color = WHITE if state == 'down' else TEXT


# ---------- Main App ----------

class MemoryVaultApp(App):
    title = 'Memory Vault'

    def build(self):
        Window.clearcolor = BG
        self.db = Database(os.path.join(self.user_data_dir, 'memoryvault.db'))
        self.img_dir = os.path.join(self.user_data_dir, 'images')
        os.makedirs(self.img_dir, exist_ok=True)
        self.page = 'home'
        self.section = None
        self.query = ''

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.search = field('Search everything', bg=WHITE)
        self.search.bind(text=self.on_search)
        self.top = top
        top.add_widget(self.search)
        root.add_widget(top)

        self.list = GridLayout(cols=1, size_hint_y=None, spacing=dp(10),
                               padding=[0, 0, 0, dp(80)])
        self.list.bind(minimum_height=self.list.setter('height'))
        sv = ScrollView()
        sv.add_widget(self.list)
        root.add_widget(sv)

        bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
        for key, name in NAV:
            t = ToggleButton(text=name, group='tabs', allow_no_selection=False,
                             state='down' if key == self.page else 'normal',
                             background_normal='', background_down='',
                             font_size=sp(14))
            t.bind(state=style_tab)
            style_tab(t, t.state)
            t.bind(on_release=lambda w, k=key: self.set_page(k))
            bar.add_widget(t)
        root.add_widget(bar)

        self.fab = Fab(text='+', pos_hint={'right': 0.96}, y=dp(78))
        self.fab.bind(on_release=lambda w: self.add_new())

        layout = FloatLayout()
        layout.add_widget(root)
        layout.add_widget(self.fab)
        self.refresh()
        return layout

    def on_start(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions
                request_permissions([
                    'android.permission.READ_EXTERNAL_STORAGE',
                    'android.permission.READ_MEDIA_IMAGES',
                ])
            except Exception:
                pass
        if not self.db.get_profile().get('name'):
            self.open_profile_form(first=True)

    # ----- pages / search -----

    def set_page(self, page):
        self.page = page
        if page == 'library':
            self.section = None
        self.search.text = ''
        self.query = ''
        show = page != 'profile'
        self.top.height = dp(44) if show else 0
        self.top.opacity = 1 if show else 0
        self.top.disabled = not show
        self.refresh()

    def open_section(self, key):
        self.section = key
        self.refresh()

    def on_search(self, widget, text):
        self.query = text
        self.refresh()

    def library_row(self, key, name):
        b = Button(text='%s   (%d)' % (name, self.db.count(key)),
                   size_hint_y=None, height=dp(56), font_size=sp(16),
                   halign='left', valign='middle', padding_x=dp(12),
                   background_normal='', background_down='',
                   background_color=WHITE, color=TEXT)
        b.bind(size=lambda w, v: setattr(w, 'text_size', (v[0] - dp(24), v[1])))
        b.bind(on_release=lambda w, k=key: self.open_section(k))
        return b

    def section_header(self):
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        back = btn('< Back', lambda w: self.open_section(None), height=40)
        back.size_hint_x = None
        back.width = dp(90)
        title = Label(text=dict(SECTIONS)[self.section], font_size=sp(18), bold=True,
                      color=TEXT, halign='left', valign='middle')
        title.bind(size=lambda w, v: setattr(w, 'text_size', v))
        row.add_widget(back)
        row.add_widget(title)
        return row

    def refresh(self):
        self.list.clear_widgets()
        show_fab = self.page == 'home' or (self.page == 'library' and bool(self.section))
        self.fab.opacity = 1 if show_fab else 0
        self.fab.disabled = not show_fab
        if self.page == 'profile':
            self.render_profile()
            return
        if self.query:
            rows = self.db.get_all(None, self.query, saved_only=(self.page == 'saved'))
            empty = 'No results found.'
        elif self.page == 'home':
            name = self.db.get_profile().get('name', '')
            self.list.add_widget(lbl(('Hello, ' + name) if name else 'Hello', 20, TEXT, True))
            self.list.add_widget(lbl('Recent memories', 13, MUTED))
            rows = self.db.get_all(limit=5)
            empty = 'No memories yet. Tap + to save your first one.'
        elif self.page == 'library':
            if not self.section:
                for key, name in SECTIONS:
                    self.list.add_widget(self.library_row(key, name))
                return
            self.list.add_widget(self.section_header())
            rows = self.db.get_all(self.section, by_event_date=(self.section == 'event'))
            empty = 'Nothing here yet. Tap + to add.'
        else:
            rows = self.db.get_all(saved_only=True)
            empty = 'No saved memories yet. Tap Save on any memory.'
        if not rows:
            self.list.add_widget(lbl(empty, 14, MUTED))
        for r in rows:
            self.list.add_widget(self.make_card(r, bool(self.query) or self.page != 'library'))

    def add_new(self):
        if self.page == 'library' and self.section:
            self.open_form(kind=self.section)
            return
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
        popup = make_popup('What do you want to save?', box, (0.85, 0.55))
        for key in ('image', 'video', 'prompt', 'event'):
            box.add_widget(btn(KIND_NAME[key],
                               lambda w, k=key: (popup.dismiss(), self.open_form(kind=k)),
                               height=48))
        box.add_widget(btn('Cancel', lambda *_: popup.dismiss(), height=44))
        popup.open()

    # ----- profile -----

    def render_profile(self):
        p = self.db.get_profile()
        card = Card()
        card.add_widget(lbl(p.get('name', ''), 20, TEXT, True))
        if p.get('about'):
            card.add_widget(lbl(p['about'], 14, TEXT))
        if p.get('interests'):
            card.add_widget(lbl('Interests: ' + p['interests'], 13, MUTED))
        card.add_widget(btn('Edit profile', lambda b: self.open_profile_form(), height=40))
        self.list.add_widget(card)
        stats = Card()
        stats.add_widget(lbl('Your vault', 14, MUTED, True))
        for key, name in SECTIONS:
            stats.add_widget(lbl('%s: %d' % (name, self.db.count(key)), 14))
        stats.add_widget(lbl('Saved: %d' % self.db.count(saved_only=True), 14))
        self.list.add_widget(stats)
        self.list.add_widget(lbl('Your data stays only on this device.', 12, MUTED))

    def open_profile_form(self, first=False):
        p = self.db.get_profile()
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
        if first:
            box.add_widget(lbl('Welcome to Memory Vault! Create your profile to start. '
                               'No phone number or email is needed, and your data '
                               'stays on this device.', 14, MUTED))
        name_in = field('Your name', text=p.get('name', ''))
        about_in = field('About you (optional)', multiline=True, height=90,
                         text=p.get('about', ''))
        int_in = field('Interests, e.g. design, travel (optional)',
                       text=p.get('interests', ''))
        err = lbl('', 13, ERROR)
        for w in (name_in, about_in, int_in, err):
            box.add_widget(w)
        popup = make_popup('Create profile' if first else 'Edit profile', box, (0.92, 0.75))

        def save(*_):
            name = name_in.text.strip()
            if not name:
                err.text = 'Name is required.'
                return
            self.db.set_profile(name=name, about=about_in.text.strip(),
                                interests=int_in.text.strip())
            popup.dismiss()
            self.refresh()

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        if not first:
            row.add_widget(btn('Cancel', lambda *_: popup.dismiss(), height=44))
        row.add_widget(btn('Save', save, True, 44))
        box.add_widget(row)
        popup.open()

    def make_card(self, r, show_type):
        card = Card()
        kind = r['kind']
        meta = fmt_dt(r['created_at'])
        if show_type:
            meta = KIND_NAME[kind] + '  |  ' + meta
        if r['pinned']:
            meta = 'Saved  |  ' + meta
        card.add_widget(lbl(meta, 12, MUTED))

        if kind == 'event' and r['event_date']:
            card.add_widget(lbl('Date: ' + iso_to_dmy(r['event_date']), 14, ACCENT, True))
        card.add_widget(lbl(r['title'], 16, TEXT, True))

        body = r['body']
        if kind == 'prompt' and len(body) > 200:
            body = body[:200] + '...'
        if body:
            card.add_widget(lbl(body, 14, TEXT))
        if kind == 'video' and r['link']:
            card.add_widget(lbl(r['link'], 12, ACCENT))

        if kind == 'prompt':
            row = BoxLayout(size_hint_y=None, height=dp(170), spacing=dp(8))
            for key, cap in (('img1', 'Normal'), ('img2', 'Result')):
                if r[key] and os.path.exists(r[key]):
                    col = BoxLayout(orientation='vertical')
                    col.add_widget(Image(source=r[key], fit_mode='contain'))
                    c = lbl(cap, 12, MUTED)
                    col.add_widget(c)
                    row.add_widget(col)
            if row.children:
                card.add_widget(row)
        elif kind == 'image' and r['img1'] and os.path.exists(r['img1']):
            card.add_widget(Image(source=r['img1'], fit_mode='contain',
                                  size_hint_y=None, height=dp(200)))

        acts = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        if kind == 'prompt':
            acts.add_widget(btn('Copy', lambda b, t=r['body']: self.copy(b, t), True, 38))
        elif kind == 'video':
            acts.add_widget(btn('Open', lambda b, u=r['link']: self.open_link(u), True, 38))
        acts.add_widget(btn('Unsave' if r['pinned'] else 'Save',
                            lambda b, i=r['id']: self.pin(i), height=38))
        acts.add_widget(btn('Edit', lambda b, e=r: self.open_form(e), height=38))
        acts.add_widget(btn('Delete', lambda b, i=r['id']: self.confirm_delete(i), height=38))
        card.add_widget(acts)
        return card

    # ----- actions -----

    def copy(self, button, text):
        Clipboard.copy(text)
        button.text = 'Copied'

    def open_link(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        if platform == 'android':
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                Activity = autoclass('org.kivy.android.PythonActivity')
                Activity.mActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                return
            except Exception:
                pass
        webbrowser.open(url)

    def pin(self, entry_id):
        self.db.toggle_pin(entry_id)
        self.refresh()

    def confirm_delete(self, entry_id):
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        box.add_widget(lbl('Delete this entry? This cannot be undone.', 15))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = make_popup('Delete', box, (0.85, 0.3))

        def do_delete(*_):
            self.db.delete(entry_id)
            popup.dismiss()
            self.refresh()

        row.add_widget(btn('Cancel', lambda *_: popup.dismiss(), height=44))
        row.add_widget(btn('Delete', do_delete, True, 44))
        box.add_widget(row)
        popup.open()

    # ----- images -----

    def store_image(self, path):
        """चुनी हुई image को app के अपने folder में copy करता है।"""
        if not path or not os.path.exists(path):
            return path or ''
        if os.path.dirname(os.path.abspath(path)) == os.path.abspath(self.img_dir):
            return path
        dest = os.path.join(self.img_dir, datetime.now().strftime('%Y%m%d%H%M%S%f')
                            + '_' + os.path.basename(path))
        try:
            shutil.copy2(path, dest)
            return dest
        except OSError:
            return path

    def pick_image(self, callback):
        start = next((p for p in ('/storage/emulated/0/DCIM', '/storage/emulated/0',
                                  os.path.expanduser('~')) if os.path.isdir(p)), '/')
        fc = FileChooserListView(
            path=start, filters=['*.png', '*.jpg', '*.jpeg', '*.webp',
                                 '*.PNG', '*.JPG', '*.JPEG'])
        box = BoxLayout(orientation='vertical', spacing=dp(6))
        box.add_widget(fc)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title='Select image', content=box, size_hint=(0.95, 0.9))

        def select(*_):
            if fc.selection:
                callback(fc.selection[0])
                popup.dismiss()

        row.add_widget(btn('Cancel', lambda *_: popup.dismiss(), height=44))
        row.add_widget(btn('Select', select, True, 44))
        box.add_widget(row)
        popup.open()

    def picker_button(self, label, key, imgs):
        b = btn(label, height=44)
        if imgs[key]:
            b.text = label + ': ' + os.path.basename(imgs[key])

        def done(path):
            imgs[key] = path
            b.text = label + ': ' + os.path.basename(path)

        b.bind(on_release=lambda *_: self.pick_image(done))
        return b

    # ----- add / edit form -----

    def open_form(self, entry=None, kind=None):
        kind = entry['kind'] if entry else (kind or self.section)

        def g(k):
            return entry[k] if entry else ''

        form = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(4))
        form.bind(minimum_height=form.setter('height'))

        title_in = field('Title', text=g('title'))
        form.add_widget(title_in)
        link_in = date_in = None
        if kind == 'video':
            link_in = field('Video link (YouTube, Instagram, ...)', text=g('link'))
            form.add_widget(link_in)
        if kind == 'event':
            date_in = field('Date (DD-MM-YYYY)', text=iso_to_dmy(g('event_date')))
            form.add_widget(date_in)
        body_in = field(BODY_HINT[kind], multiline=True,
                        height=170 if kind == 'prompt' else 120, text=g('body'))
        form.add_widget(body_in)

        imgs = {'img1': g('img1'), 'img2': g('img2')}
        if kind == 'prompt':
            form.add_widget(self.picker_button('Normal image', 'img1', imgs))
            form.add_widget(self.picker_button('Result image', 'img2', imgs))
        elif kind == 'image':
            form.add_widget(self.picker_button('Choose image', 'img1', imgs))

        err = lbl('', 13, ERROR)
        sv = ScrollView()
        sv.add_widget(form)
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(6))
        content.add_widget(sv)
        content.add_widget(err)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        content.add_widget(row)
        popup = make_popup(('Edit ' if entry else 'New ') + KIND_NAME[kind], content)

        def save(*_):
            title = title_in.text.strip()
            if not title:
                err.text = 'Title is required.'
                return
            data = {'title': title, 'body': body_in.text.strip()}
            if kind == 'video':
                if not link_in.text.strip():
                    err.text = 'Video link is required.'
                    return
                data['link'] = link_in.text.strip()
            if kind == 'event':
                try:
                    data['event_date'] = dmy_to_iso(date_in.text)
                except ValueError:
                    err.text = 'Date must be like 05-11-2026.'
                    return
            if kind == 'image' and not imgs['img1']:
                err.text = 'Please choose an image.'
                return
            if kind in ('prompt', 'image'):
                data['img1'] = self.store_image(imgs['img1'])
            if kind == 'prompt':
                data['img2'] = self.store_image(imgs['img2'])
            if entry:
                self.db.update(entry['id'], **data)
            else:
                self.db.add(kind, **data)
            popup.dismiss()
            self.refresh()

        row.add_widget(btn('Cancel', lambda *_: popup.dismiss(), height=44))
        row.add_widget(btn('Save', save, True, 44))
        popup.open()


if __name__ == '__main__':
    MemoryVaultApp().run()
