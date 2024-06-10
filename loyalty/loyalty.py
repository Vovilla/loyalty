import reflex as rx
import yaml

from rxconfig import config
import datetime

import sqlmodel
import sqlalchemy


config = None

department_base = dict()

def load_config():
    with open('config.yaml', 'r') as file:
        global config
        config = yaml.safe_load(file)
     
load_config()


class Achievement(rx.Model, table=True):
    employee: str
    department: str
    achievement: str
    point: str
    update_ts: datetime.datetime = sqlmodel.Field(
        default=None,
        sa_column=sqlalchemy.Column(
            "update_ts",
            sqlalchemy.DateTime(timezone=True),
            server_default=sqlalchemy.func.now(),
        ),
    )

    def dict(self, *args, **kwargs) -> dict:
        d = super().dict(*args, **kwargs)
        del d["_sa_instance_state"]
        d["update_ts"] = self.update_ts.replace(
            microsecond=0
        ).isoformat()
        return d


class AddTabState(rx.State):
    form_data: dict = {}

    def handle_submit(self, form_data: dict):
        """Handle the form submit."""
        self.form_data = form_data
        if self.department_present():
            self.add_achievement()
        elif department := self.get_saved_department():
            self.form_data['department'] = department
            self.add_achievement()
        else:
            return rx.window_alert(f"Не удалось найти отдел для сотрудника {self.form_data['employee']}")

    def department_present(self):
        return self.form_data['department'] and (self.form_data['department'] in config['department'])

    def get_saved_department(self):
        with rx.session() as session:
            employee = self.form_data['employee']
            department = session.exec(sqlalchemy.text(
                f"SELECT department FROM Achievement WHERE employee = '{employee}' ORDER BY id DESC"
            )).first()
            if department:
                department = department[0]
            return department
       
    def add_achievement(self):
        with rx.session() as session:
            session.add(
                Achievement(
                    employee=self.form_data['employee'],
                    department=self.form_data['department'],
                    achievement=self.form_data['achievement'],
                    point=self.form_data['point'],
                )
            )
            session.commit()


def make_add_tab() -> rx.Component:
    return rx.container(
        rx.form.root(
            rx.vstack(
                rx.input(
                    name="employee",
                    placeholder="ФИО сотрудника",
                    required=True,
                ),
                rx.select(
                    config['department'],
                    name="department",
                    color="pink",
                    variant="soft",
                    radius="full",
                    placeholder="Отдел"
                ),
                rx.input(
                    name="achievement",
                    placeholder="Достижение",
                    required=True,
                ),
                rx.input(
                    name="point",
                    placeholder="Балл",
                    required=True,
                ),
                rx.button("Добавить", type="submit"),
            ),
            on_submit=AddTabState.handle_submit,
            reset_on_submit=True,
            width="100%",
        ),
    )

class ViewTabState(rx.State):
    
    points: int

    achievements: list[tuple]
    
    achievements_json: list[dict]

    def handle_submit(self, form_data: dict):
        achievements = self.select_achievements(form_data['employee'])
        self.achievements_json = achievements
        self.achievements = [
            (
                a['id'],
                a['employee'],
                a['department'],
                a['achievement'],
                a['point'],
                a['update_ts'],
            )
            for a in achievements
        ]
        self.points = sum(int(a['point']) for a in achievements)
                
    def select_achievements(self, name: str):
        achievements = None
        with rx.session() as session:
            if name:
                achievements = session.exec(
                        Achievement.select().where(
                            Achievement.employee.contains(name)
                        )
                    ).all()
            else:
                achievements = session.exec(Achievement.select()).all()
        return [{key: value for key, value in dict(row).items() if key != '_sa_instance_state'} for row in achievements]

def make_view_tab() -> rx.Component:
    return rx.container(
        rx.form.root(
            rx.vstack(
                rx.input(
                    name="employee",
                    placeholder="ФИО сотрудника",
                ),
                rx.chakra.table(
                    headers = ["id", "Сотрудник", "Отдел", "Достижение", "Балл", "Время"],
                    rows = ViewTabState.achievements
                ),
                rx.divider(width="100%"),
                rx.heading("Баллы"),
                rx.text(ViewTabState.points.to_string()),
                rx.button("Найти", type="submit"),
                rx.hstack(
                    rx.button(
                        "Скачать JSON",
                        on_click=rx.download(
                            data=ViewTabState.achievements_json,
                            filename="achievements.json",
                        ),
                    ),
                    spacing="7",
                ),
            ),
            on_submit=ViewTabState.handle_submit,
            reset_on_submit=True,
            width="100%",
        ),
    )
    
  
class RemoveTabState(rx.State):

    def handle_submit(self, form_data: dict):
        with rx.session() as session:
            row = session.exec(
                Achievement.select().where(
                    Achievement.id == int(form_data['id'])
                )
            ).first()
            session.delete(row)
            session.commit()
    
    
def make_remove_tab() -> rx.Component:
    return rx.container(
        rx.form.root(
            rx.vstack(
                rx.input(
                    name="id",
                    placeholder="id достижения",
                ),
                rx.button("Удалить", type="submit"),
            ),
            on_submit=RemoveTabState.handle_submit,
            reset_on_submit=True,
            width="100%",
        ),
    )

def index() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.heading("Программа лояльности сотрудников НИИМЭ", size="9"),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Добавить", value="add_tab"),
                rx.tabs.trigger("Поиск", value="view_tab"),
                rx.tabs.trigger("Удалить", value="remove_tab"),
            ),
            rx.tabs.content(
                make_add_tab(),
                value="add_tab",
            ),
            rx.tabs.content(
                make_view_tab(),
                value="view_tab",
            ),
            rx.tabs.content(
                make_remove_tab(),
                value="remove_tab",
            ),
            default_value="add_tab",
        )
    )


app = rx.App()
app.add_page(index)