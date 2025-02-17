from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView 
from collections import deque
from kivy.uix.widget import Widget


def get_last_unique_numbers(numbers, limit):
    """Returns up to 'limit' unique numbers from 'numbers' by first appearance, reversed."""
    seen = {}
    for index, number in enumerate(numbers):
        if number not in seen:
            seen[number] = index
    sorted_by_first_appearance = sorted(seen.keys(), key=lambda x: seen[x])
    return sorted_by_first_appearance[-limit:][::-1]


class RouletteTrackerApp(App):
    def build(self):
        self.pages = []
        for _ in range(5):
            self.pages.append({
                "last_numbers": deque(maxlen=37),
                "cycle_count": 1,
                "reset_cycle_on_next_input": False,
                "cycle_history": deque(maxlen=5),
                "unique_limit": 16,
                "current_hit": None,
                "grid_unique": [],
                "force_cycle_to_one": False
            })
        self.current_page = 0

        main_layout = BoxLayout(orientation='vertical', spacing=5, padding=5)

        self.title_label = Label(
            text=f"Current Limit: {self.pages[self.current_page]['unique_limit']}",
            size_hint=(1, 0.04),
            color=(1, 0.5, 0, 1),  # Orange color
            font_size='20sp'
        )
        main_layout.add_widget(self.title_label)

        # Top input bar
        top_section = BoxLayout(orientation='horizontal', size_hint=(1, 0.12), spacing=5)
        self.number_input = TextInput(
            text='',
            hint_text='Enter number 0-36 (Press Enter)',
            input_filter='int',
            size_hint=(0.7, 1),
            multiline=False
        )
        self.number_input.bind(on_text_validate=self.on_submit)
        btn_submit = Button(text='Submit', size_hint=(0.3, 1))
        btn_submit.bind(on_press=self.on_submit)
        top_section.add_widget(self.number_input)
        top_section.add_widget(btn_submit)
        main_layout.add_widget(top_section)

        # Page selection
        page_select_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.06), spacing=5)
        self.page_buttons = []
        for i in range(5):
            btn = Button(text=f"Page {i+1}", size_hint=(0.2, 1))
            btn.bind(on_press=lambda inst, idx=i: self.switch_page(idx))
            page_select_layout.add_widget(btn)
            self.page_buttons.append(btn)
        main_layout.add_widget(page_select_layout)

        # 4x4 grid + cycle display
        grid_cycle_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.3), spacing=5)

        self.grid_layout = GridLayout(cols=4, rows=4, size_hint=(0.7, 1))
        self.grid_labels = []
        for row in reversed(range(4)):
            row_labels = []
            for col in range(4):
                lbl = Label(text="", font_size='20sp')
                row_labels.append(lbl)
                self.grid_layout.add_widget(lbl)
            self.grid_labels.append(row_labels)
        grid_cycle_layout.add_widget(self.grid_layout)

        cycle_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1), padding=(10, 0))
        self.cycle_labels = []
        for _ in range(6):
            lbl = Label(text="", font_size='14sp', halign='left', valign='middle')
            lbl.bind(size=lambda lbl, _: lbl.setter('text_size')(lbl, (lbl.width, None)))
            self.cycle_labels.append(lbl)
            cycle_layout.add_widget(lbl)
        grid_cycle_layout.add_widget(cycle_layout)

        main_layout.add_widget(grid_cycle_layout)

        # Middle section (Last 37)
        middle_section = BoxLayout(orientation='vertical', size_hint=(1, 0.60))
        middle_section.add_widget(Label(
            text="Last 37 Numbers",
            size_hint=(1, 0.1),
            color=(0.5, 0.9, 1, 1),
            font_size='20sp'
        ))
        middle_section.add_widget(Widget(size_hint_y=None, height=50))

        # SCROLLVIEW + GRID: top-aligned
        scrollview = ScrollView(size_hint=(1, 0.9))
        # Key property changes:
        self.number_grid = GridLayout(
            cols=10,
            orientation='rl-tb',   # 1) Fill Left→Right, then Top→Bottom
            size_hint=(1, None),    # 2) We'll let the height grow to fit children
            spacing = 40
        )
        # 3) Bind the grid's minimum_height to its height: top row stays at top
        self.number_grid.bind(minimum_height=self.number_grid.setter('height'))
        scrollview.add_widget(self.number_grid)
        middle_section.add_widget(scrollview)
        main_layout.add_widget(middle_section)

        # Action buttons
        actions_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        btn_set_limit = Button(text='Set Limit', size_hint=(0.2, 1))
        btn_edit = Button(text='Edit', size_hint=(0.6, 1))
        btn_restart = Button(text='Restart', size_hint=(0.2, 1))
        btn_set_limit.bind(on_press=self.show_limit_popup)
        btn_edit.bind(on_press=self.edit_numbers)
        btn_restart.bind(on_press=self.confirm_restart)
        actions_layout.add_widget(btn_set_limit)
        actions_layout.add_widget(btn_edit)
        actions_layout.add_widget(btn_restart)
        main_layout.add_widget(actions_layout)

        self.load_page_data(0)
        self.update_page_button_colors()
        return main_layout

    #  SUBMIT LOGIC
    def on_submit(self, instance):
        user_input = self.number_input.text.strip()
        page = self.pages[self.current_page]

        if user_input.isdigit():
            number = int(user_input)
            if 0 <= number <= 36:

                if page["reset_cycle_on_next_input"] and page["current_hit"]:
                    page["cycle_history"].append(page["current_hit"])
                    page["current_hit"] = None
                    page["reset_cycle_on_next_input"] = False

                if page["force_cycle_to_one"]:
                    page["cycle_count"] = 0
                    page["force_cycle_to_one"] = False

                page["cycle_count"] += 1
                old_grid = page["grid_unique"]
                is_duplicate = (number in old_grid)
                if is_duplicate:
                    try:
                        old_position = old_grid.index(number) + 1
                    except ValueError:
                        old_position = 0
                    page["current_hit"] = ('hit', page["cycle_count"], number, old_position)
                    page["reset_cycle_on_next_input"] = True
                    page["force_cycle_to_one"] = True

                page["last_numbers"].append(number)
                self.update_number_grid()
                self.update_4x4_grid()
                self.update_cycle_display()
                self.number_input.text = ''

    # 4x4 GRID
    def update_4x4_grid(self):
        page = self.pages[self.current_page]
        if len(page["last_numbers"]) < 37:
            for row in range(4):
                for col in range(4):
                    self.grid_labels[row][col].text = ""
            page["grid_unique"] = []
            return

        numbers = get_last_unique_numbers(page["last_numbers"], page["unique_limit"])[:16]
        page["grid_unique"] = numbers
        index = 0
        for row in range(3, -1, -1):
            for col in range(4):
                if index < len(numbers):
                    self.grid_labels[3 - row][col].text = str(numbers[index])
                    self.grid_labels[3 - row][col].color = (0, 1, 0, 1) if index < 8 else (1, 1, 1, 1)
                    index += 1
                else:
                    self.grid_labels[3 - row][col].text = ""
                    self.grid_labels[3 - row][col].color = (1, 1, 1, 1)

    # CURRENT + LAST 1..5
    def update_cycle_display(self):
        page = self.pages[self.current_page]

        if page["current_hit"]:
            _, cycle_num, number, position = page["current_hit"]
            self.cycle_labels[0].text = f"Current: C{cycle_num}({number}, S{position})"
            self.cycle_labels[0].color = (0, 1, 0, 1)
        else:
            current_number = page["last_numbers"][-1] if page["last_numbers"] else "-"
            self.cycle_labels[0].text = f"Current: C{page['cycle_count']}({current_number})"
            self.cycle_labels[0].color = (1, 1, 1, 1)

        for i in range(5):
            label_index = i + 1
            lbl = self.cycle_labels[label_index]
            if i < len(page["cycle_history"]):
                _, cycle_num, number, old_position = page["cycle_history"][-(i+1)]
                lbl.text = f"Last {i+1}: C{cycle_num}({number}, S{old_position})"
                lbl.color = (1, 1, 0, 1)
            else:
                lbl.text = ""
                lbl.color = (1, 1, 1, 1)

    # LAST 37 GRID
    def update_number_grid(self):
        """
        Show the spins top-aligned (first row at top, new rows below).
        The grid is in a ScrollView, orientation='lr-tb', size_hint=(1,None).
        We just add each item left→right, top→bottom in order:
        """
        page = self.pages[self.current_page]
        self.number_grid.clear_widgets()
        for number in page["last_numbers"]:
            lbl = Label(text=str(number), size_hint_y=None, height=30)
            self.number_grid.add_widget(lbl)

        # The grid's height automatically updates from the 'minimum_height' binding

    # PAGE SWITCH
    def switch_page(self, new_page_index):
        if new_page_index == self.current_page:
            return
        self.current_page = new_page_index
        self.load_page_data(new_page_index)
        self.update_page_button_colors()

    def update_page_button_colors(self):
        for i, btn in enumerate(self.page_buttons):
            # Current page gets the vibrant blue, others get gray
            if i == self.current_page:
                btn.background_color = (0, 0.47, 0.95, 1)  # New blue color
                btn.color = (1, 1, 1, 1)  # White text
            else:
                btn.background_color = (0.3, 0.3, 0.3, 1)  # Darker gray
                btn.color = (0.7, 0.7, 0.7, 1)  # Light gray text

    def load_page_data(self, page_index):
        self.update_4x4_grid()
        self.update_cycle_display()
        self.update_number_grid()

    # SET LIMIT
    def show_limit_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)
        popup = Popup(title='Set Unique Limit', content=content, size_hint=(0.6, 0.4))

        limit_input = TextInput(
            text=str(self.pages[self.current_page]["unique_limit"]),
            input_filter='int',
            multiline=False
        )
        content.add_widget(limit_input)

        btn_box = BoxLayout(size_hint_y=None, height=50)

        def set_limit_and_close(_):
            self.set_limit(limit_input.text, popup)

        limit_input.bind(on_text_validate=lambda _: set_limit_and_close(None))
        btn_box.add_widget(Button(text='OK', on_press=set_limit_and_close))
        btn_box.add_widget(Button(text='Cancel', on_press=popup.dismiss))

        content.add_widget(btn_box)
        popup.open()

    def set_limit(self, limit, popup):
        try:
            limit = int(limit)
            limit = max(1, min(16, limit))
            self.pages[self.current_page]["unique_limit"] = limit
            self.update_4x4_grid()
            self.update_cycle_display()
            self.title_label.text = f"Roulette App (Current Limit: {limit})"
            popup.dismiss()
        except ValueError:
            pass

    # EDIT NUMBERS
    def edit_numbers(self, instance):
        page = self.pages[self.current_page]
        box = BoxLayout(orientation='vertical', spacing=5, padding=10)

        text_edit = TextInput(
            text=', '.join(map(str, page["last_numbers"])),
            multiline=True,
            size_hint_y=None,
            height=200
        )
        box.add_widget(text_edit)

        spacer = Widget(size_hint_y=1)
        box.add_widget(spacer)

        btn_layout = BoxLayout(size_hint_y=None, height=50)
        popup = Popup(title='Edit Numbers', content=box, size_hint=(0.8, 0.4))

        def save_changes(_):
            new_numbers = []
            for part in text_edit.text.split(','):
                part = part.strip()
                if part.isdigit() and 0 <= int(part) <= 36:
                    new_numbers.append(int(part))
            page["last_numbers"].clear()
            page["last_numbers"].extend(new_numbers[-37:])
            page["current_hit"] = None
            page["cycle_history"].clear()
            page["cycle_count"] = 1
            page["reset_cycle_on_next_input"] = False
            page["grid_unique"] = []
            page["force_cycle_to_one"] = False
            self.load_page_data(self.current_page)
            popup.dismiss()

        text_edit.bind(on_text_validate=lambda _: save_changes(None))
        btn_layout.add_widget(Button(text='Save', on_press=save_changes))
        btn_layout.add_widget(Button(text='Cancel', on_press=popup.dismiss))
        box.add_widget(btn_layout)
        popup.open()

    # RESTART
    def confirm_restart(self, instance):
        box = BoxLayout(orientation='vertical', padding=10)
        btn_layout = BoxLayout(height=50, size_hint_y=None)
        popup = Popup(title='Confirm Restart', content=box, size_hint=(0.6, 0.4))

        box.add_widget(Label(text="Are you sure you want to restart?"))
        btn_layout.add_widget(Button(text='Yes', on_press=lambda x: [self.reset_app(), popup.dismiss()]))
        btn_layout.add_widget(Button(text='No', on_press=popup.dismiss))
        box.add_widget(btn_layout)
        popup.open()

    def reset_app(self):
        for page in self.pages:
            page["last_numbers"].clear()
            page["cycle_count"] = 1
            page["reset_cycle_on_next_input"] = False
            page["cycle_history"].clear()
            page["current_hit"] = None
            page["grid_unique"] = []
            page["force_cycle_to_one"] = False
        self.load_page_data(self.current_page)


if __name__ == '__main__':
    RouletteTrackerApp().run()
