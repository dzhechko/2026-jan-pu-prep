"""CBT lesson service – content retrieval and progress tracking."""

from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import CBTLesson, UserLessonProgress
from app.models.pattern import Pattern
from app.schemas.lesson import (
    LessonData,
    LessonListItem,
    LessonResponse,
    LessonsListResponse,
    ProgressData,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Seed data: 20 CBT lessons in Russian
# ---------------------------------------------------------------------------

LESSON_CONTENT: list[dict] = [
    # --- Lessons 1-5: Awareness & observation ---
    {
        "lesson_order": 1,
        "title": "Что такое осознанное питание",
        "content_md": (
            "## Введение в осознанное питание\n\n"
            "Осознанное питание — это практика внимательного отношения к тому, что, "
            "когда и почему вы едите. Вместо автоматического потребления пищи мы учимся "
            "замечать свои ощущения, мысли и эмоции во время еды.\n\n"
            "**Упражнение:** В течение следующего приёма пищи попробуйте есть медленно, "
            "обращая внимание на вкус, текстуру и аромат каждого кусочка. Отложите телефон "
            "и сосредоточьтесь только на еде."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 2,
        "title": "Дневник питания как инструмент",
        "content_md": (
            "## Зачем вести дневник питания\n\n"
            "Дневник питания — это мощный инструмент самонаблюдения. Записывая каждый "
            "приём пищи, вы начинаете видеть паттерны, которые раньше оставались незаметными. "
            "Исследования показывают, что само по себе ведение дневника помогает улучшить "
            "пищевые привычки.\n\n"
            "**Упражнение:** Начните записывать не только то, что вы едите, но и время, "
            "место, настроение и уровень голода. Через неделю вы увидите свои первые паттерны."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 3,
        "title": "Шкала голода и сытости",
        "content_md": (
            "## Научитесь различать голод и сытость\n\n"
            "Многие из нас потеряли связь с естественными сигналами тела о голоде и сытости. "
            "Шкала от 1 до 10 поможет вам заново научиться распознавать эти сигналы: "
            "1 — сильный голод, 5 — нейтральное состояние, 10 — переедание.\n\n"
            "**Упражнение:** Перед каждым приёмом пищи оцените свой уровень голода по шкале. "
            "Старайтесь начинать есть при 3-4 и заканчивать при 6-7. Запишите свои наблюдения."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 4,
        "title": "Автоматические мысли о еде",
        "content_md": (
            "## Распознаём автоматические мысли\n\n"
            "Когнитивно-поведенческая терапия учит нас, что наши мысли влияют на поведение. "
            "Автоматические мысли о еде часто появляются бессознательно: «Я заслужил это», "
            "«Один кусочек не повредит», «Раз уж я начал, продолжу».\n\n"
            "**Упражнение:** В течение дня замечайте мысли, связанные с едой. Записывайте их "
            "без оценки. Просто наблюдайте, как часто они появляются и в каких ситуациях."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 5,
        "title": "Триггеры переедания",
        "content_md": (
            "## Определяем триггеры\n\n"
            "Триггер — это стимул, который запускает определённое пищевое поведение. "
            "Триггеры бывают внешние (запах еды, реклама, вид еды у коллеги) и внутренние "
            "(стресс, скука, усталость, грусть). Понимание своих триггеров — первый шаг "
            "к управлению ими.\n\n"
            "**Упражнение:** Составьте список ваших 5 главных триггеров. Для каждого "
            "запишите: что обычно происходит, что вы чувствуете и что едите в результате."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    # --- Lessons 6-10: Emotional eating ---
    {
        "lesson_order": 6,
        "title": "Эмоциональный голод vs физический",
        "content_md": (
            "## Различаем виды голода\n\n"
            "Эмоциональный голод приходит внезапно, требует определённой еды и не утоляется "
            "даже при полном желудке. Физический голод нарастает постепенно, удовлетворяется "
            "любой пищей и проходит после еды.\n\n"
            "**Упражнение:** Когда вы чувствуете желание поесть, остановитесь и спросите: "
            "«Это физический голод или эмоциональная потребность?». Если эмоциональная — "
            "попробуйте назвать эмоцию, которую вы испытываете."
        ),
        "pattern_tags": ["mood"],
        "duration_min": 5,
    },
    {
        "lesson_order": 7,
        "title": "Стресс и переедание",
        "content_md": (
            "## Как стресс влияет на питание\n\n"
            "При стрессе организм вырабатывает кортизол, который усиливает тягу к сладкой "
            "и жирной пище. Это эволюционный механизм, но в современном мире он приводит "
            "к хроническому перееданию. Понимание этой связи помогает разорвать цикл.\n\n"
            "**Упражнение:** Освойте технику «4-7-8»: вдох на 4 счёта, задержка на 7, "
            "выдох на 8. Используйте её, когда чувствуете стресс и тягу к еде. "
            "Запишите, помогло ли это."
        ),
        "pattern_tags": ["mood"],
        "duration_min": 5,
    },
    {
        "lesson_order": 8,
        "title": "Скука и привычка есть",
        "content_md": (
            "## Еда как развлечение\n\n"
            "Скука — один из самых распространённых триггеров эмоционального переедания. "
            "Мы привыкаем использовать еду как способ занять себя, особенно при просмотре "
            "телевизора или прокрутке соцсетей.\n\n"
            "**Упражнение:** Составьте список из 10 приятных занятий, не связанных с едой: "
            "прогулка, звонок другу, чтение, головоломка. Когда чувствуете скуку — выбирайте "
            "что-то из списка вместо похода к холодильнику."
        ),
        "pattern_tags": ["mood"],
        "duration_min": 5,
    },
    {
        "lesson_order": 9,
        "title": "Техника СТОП для эмоций",
        "content_md": (
            "## Метод СТОП\n\n"
            "Когда эмоции подталкивают к еде, используйте технику СТОП: "
            "**С** — стой (остановись на минуту), **Т** — тело (что чувствует тело?), "
            "**О** — обдумай (что на самом деле мне нужно?), **П** — поступай осознанно.\n\n"
            "**Упражнение:** Практикуйте технику СТОП каждый раз, когда тянетесь к еде "
            "не по голоду. Записывайте результаты в дневник. Со временем это станет "
            "автоматической привычкой."
        ),
        "pattern_tags": ["mood"],
        "duration_min": 5,
    },
    {
        "lesson_order": 10,
        "title": "Самосострадание вместо самокритики",
        "content_md": (
            "## Будьте добры к себе\n\n"
            "Исследования показывают, что самокритика после переедания усиливает цикл "
            "эмоционального переедания. Самосострадание, напротив, помогает разорвать "
            "этот цикл. Относитесь к себе как к лучшему другу.\n\n"
            "**Упражнение:** Если вы переели — вместо мысли «Я безвольный» скажите себе: "
            "«Это сложная привычка, и я учусь с ней справляться. Каждый день — новая "
            "возможность». Запишите три вещи, которые вы делаете хорошо."
        ),
        "pattern_tags": ["mood"],
        "duration_min": 5,
    },
    # --- Lessons 11-14: Time & routine ---
    {
        "lesson_order": 11,
        "title": "Режим питания и биоритмы",
        "content_md": (
            "## Когда мы едим — так же важно, как что\n\n"
            "Наш организм работает по циркадным ритмам. Метаболизм наиболее активен "
            "в первой половине дня и замедляется вечером. Регулярный режим питания помогает "
            "организму эффективнее использовать питательные вещества.\n\n"
            "**Упражнение:** Установите примерное время для трёх основных приёмов пищи "
            "и придерживайтесь его в течение недели. Отмечайте, как меняется ваше самочувствие."
        ),
        "pattern_tags": ["time", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 12,
        "title": "Опасность пропуска приёмов пищи",
        "content_md": (
            "## Почему нельзя пропускать еду\n\n"
            "Пропуск завтрака или обеда часто приводит к перееданию вечером. Когда уровень "
            "сахара в крови падает, мозг включает режим «экстренного питания» — мы теряем "
            "контроль и выбираем наиболее калорийную пищу.\n\n"
            "**Упражнение:** Если вы склонны пропускать приёмы пищи — подготовьте "
            "здоровые перекусы заранее: орехи, фрукты, йогурт. Поставьте напоминание "
            "на обед в телефоне."
        ),
        "pattern_tags": ["time", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 13,
        "title": "Вечернее переедание",
        "content_md": (
            "## Разбираемся с ночными набегами\n\n"
            "Вечернее и ночное переедание — одна из самых распространённых проблем. "
            "Причины: недоедание днём, стресс после рабочего дня, привычка есть перед "
            "телевизором. Понимание причины — ключ к решению.\n\n"
            "**Упражнение:** В течение недели записывайте, что вы чувствуете перед "
            "вечерним перекусом. Голод? Стресс? Скука? Привычка? На основе этого "
            "выберите подходящую стратегию из предыдущих уроков."
        ),
        "pattern_tags": ["time", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 14,
        "title": "Планирование питания",
        "content_md": (
            "## Планируем заранее\n\n"
            "Исследования показывают, что люди, которые планируют питание заранее, "
            "потребляют меньше калорий и делают более здоровый выбор. Планирование "
            "снимает необходимость принимать решения в момент голода.\n\n"
            "**Упражнение:** В воскресенье составьте примерное меню на неделю. "
            "Необязательно следовать ему точно — важен сам процесс планирования. "
            "Закупите продукты по списку, чтобы здоровая еда была под рукой."
        ),
        "pattern_tags": ["time", "skip"],
        "duration_min": 5,
    },
    # --- Lessons 15-17: Context awareness ---
    {
        "lesson_order": 15,
        "title": "Влияние окружения на еду",
        "content_md": (
            "## Контекст определяет выбор\n\n"
            "Исследования показывают, что размер тарелки, освещение, музыка и компания "
            "влияют на количество съеденного. В ресторане мы обычно едим на 30-50% больше, "
            "чем дома. Осознание влияния контекста — мощный инструмент управления.\n\n"
            "**Упражнение:** Обратите внимание на обстановку во время еды. Попробуйте "
            "использовать тарелки меньшего размера, убрать отвлекающие факторы и есть "
            "за столом, а не на ходу."
        ),
        "pattern_tags": ["context"],
        "duration_min": 5,
    },
    {
        "lesson_order": 16,
        "title": "Социальное питание",
        "content_md": (
            "## Еда в компании\n\n"
            "Мы едим значительно больше, когда едим с другими людьми — это называется "
            "«социальная фасилитация». В компании из 7+ человек потребление может вырасти "
            "на 96%. Это нормальный эффект, но о нём важно знать.\n\n"
            "**Упражнение:** Перед обедом с друзьями или на вечеринке решите заранее, "
            "сколько вы хотите съесть. Сосредоточьтесь на общении, а не на еде. "
            "Положите на тарелку желаемую порцию и не берите добавку автоматически."
        ),
        "pattern_tags": ["context"],
        "duration_min": 5,
    },
    {
        "lesson_order": 17,
        "title": "Осознанный выбор вне дома",
        "content_md": (
            "## Стратегии для ресторанов и кафе\n\n"
            "Меню ресторанов спроектировано так, чтобы стимулировать аппетит: красочные "
            "описания, комбо-предложения, десертное меню в конце. Зная эти приёмы, вы "
            "можете делать осознанный выбор вместо импульсивного.\n\n"
            "**Упражнение:** В следующий раз в ресторане: 1) Выберите блюдо до прихода, "
            "просмотрев меню онлайн. 2) Попросите соус отдельно. 3) Оставьте порцию "
            "на следующий раз, если она большая. Отметьте, как это повлияло на самочувствие."
        ),
        "pattern_tags": ["context"],
        "duration_min": 5,
    },
    # --- Lessons 18-20: Integration & maintenance ---
    {
        "lesson_order": 18,
        "title": "Когнитивная реструктуризация",
        "content_md": (
            "## Меняем мышление о еде\n\n"
            "Когнитивная реструктуризация — ключевая техника КПТ. Мы учимся замечать "
            "искажённые мысли о еде и заменять их более реалистичными. Например: "
            "«Я должен доесть всё» -> «Я могу остановиться, когда сыт».\n\n"
            "**Упражнение:** Запишите 3 типичных мысли об еде, которые вас беспокоят. "
            "Для каждой найдите: 1) Какое когнитивное искажение это? 2) Как можно "
            "переформулировать мысль более реалистично?"
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 19,
        "title": "Предотвращение рецидивов",
        "content_md": (
            "## Срыв — это не провал\n\n"
            "Рецидивы — нормальная часть процесса изменений. Важно не то, что вы "
            "сорвались, а как вы реагируете на срыв. Стратегия предотвращения рецидивов "
            "включает: распознавание ранних предупреждающих сигналов и план действий.\n\n"
            "**Упражнение:** Составьте свой «план на случай срыва»: 1) Мои предупреждающие "
            "сигналы (например, пропуск обеда, плохое настроение). 2) Мои действия "
            "(техника СТОП, звонок другу, прогулка). 3) Слова поддержки для себя."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
    {
        "lesson_order": 20,
        "title": "Долгосрочная стратегия",
        "content_md": (
            "## Поддержание результатов\n\n"
            "Вы прошли 20 уроков и освоили ключевые инструменты КПТ для работы "
            "с пищевым поведением. Долгосрочный успех зависит от регулярной практики "
            "и постепенного превращения новых навыков в привычки.\n\n"
            "**Упражнение:** Выберите 3 техники из курса, которые оказались наиболее "
            "полезными для вас. Запланируйте, как вы будете использовать их ежедневно. "
            "Продолжайте вести дневник питания — это ваш главный инструмент самонаблюдения."
        ),
        "pattern_tags": ["time", "mood", "context", "skip"],
        "duration_min": 5,
    },
]


async def get_progress(db: AsyncSession, user_id: UUID) -> ProgressData:
    """Return overall lesson completion progress for a user."""
    total_stmt = select(func.count()).select_from(CBTLesson)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    completed_stmt = (
        select(func.count())
        .select_from(UserLessonProgress)
        .where(UserLessonProgress.user_id == user_id)
    )
    completed_result = await db.execute(completed_stmt)
    current = completed_result.scalar_one()

    return ProgressData(current=current, total=total)


async def get_lesson(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> LessonResponse | None:
    """Return a lesson by ID with progress context."""
    stmt = select(CBTLesson).where(CBTLesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if lesson is None:
        return None

    progress = await get_progress(db, user_id)

    return LessonResponse(
        lesson=LessonData(
            id=lesson.id,
            title=lesson.title,
            content_md=lesson.content_md,
            duration_min=lesson.duration_min,
        ),
        progress=progress,
    )


async def complete_lesson(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> bool:
    """Mark a lesson as completed. Returns True if newly completed."""
    # Check if already completed
    existing = await db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False  # Already completed

    progress = UserLessonProgress(user_id=user_id, lesson_id=lesson_id)
    db.add(progress)
    await db.flush()

    logger.info(
        "lesson_completed",
        user_id=str(user_id),
        lesson_id=str(lesson_id),
    )
    return True


async def get_all_lessons(
    db: AsyncSession,
    user_id: UUID,
) -> LessonsListResponse:
    """Return all CBT lessons ordered by lesson_order, with completion status."""
    # Fetch all lessons ordered by lesson_order
    lessons_stmt = select(CBTLesson).order_by(CBTLesson.lesson_order)
    lessons_result = await db.execute(lessons_stmt)
    lessons = lessons_result.scalars().all()

    # Fetch completed lesson IDs for this user
    completed_stmt = (
        select(UserLessonProgress.lesson_id)
        .where(UserLessonProgress.user_id == user_id)
    )
    completed_result = await db.execute(completed_stmt)
    completed_ids = {row[0] for row in completed_result.all()}

    items = [
        LessonListItem(
            id=lesson.id,
            title=lesson.title,
            lesson_order=lesson.lesson_order,
            duration_min=lesson.duration_min,
            completed=lesson.id in completed_ids,
        )
        for lesson in lessons
    ]

    total = len(lessons)
    current = len(completed_ids)

    return LessonsListResponse(
        lessons=items,
        progress=ProgressData(current=current, total=total),
    )


async def get_recommended_lesson(
    db: AsyncSession,
    user_id: UUID,
) -> LessonResponse | None:
    """Return the next recommended lesson based on user's active patterns.

    Priority:
    1. First uncompleted lesson whose pattern_tags overlap with the user's active pattern types.
    2. Fallback: first uncompleted lesson by lesson_order.
    3. If all lessons completed: return None.
    """
    # Load user's active pattern types
    patterns_stmt = (
        select(Pattern.type)
        .where(Pattern.user_id == user_id, Pattern.active == True)  # noqa: E712
    )
    patterns_result = await db.execute(patterns_stmt)
    user_pattern_types = {row[0] for row in patterns_result.all()}

    # Fetch all lessons ordered by lesson_order
    lessons_stmt = select(CBTLesson).order_by(CBTLesson.lesson_order)
    lessons_result = await db.execute(lessons_stmt)
    all_lessons = lessons_result.scalars().all()

    # Fetch completed lesson IDs for this user
    completed_stmt = (
        select(UserLessonProgress.lesson_id)
        .where(UserLessonProgress.user_id == user_id)
    )
    completed_result = await db.execute(completed_stmt)
    completed_ids = {row[0] for row in completed_result.all()}

    # Find uncompleted lessons
    uncompleted = [l for l in all_lessons if l.id not in completed_ids]

    if not uncompleted:
        return None

    # Try to find a lesson matching user's patterns
    recommended = None
    if user_pattern_types:
        for lesson in uncompleted:
            tags = set(lesson.pattern_tags or [])
            if tags & user_pattern_types:
                recommended = lesson
                break

    # Fallback: first uncompleted lesson by lesson_order
    if recommended is None:
        recommended = uncompleted[0]

    progress = await get_progress(db, user_id)

    return LessonResponse(
        lesson=LessonData(
            id=recommended.id,
            title=recommended.title,
            content_md=recommended.content_md,
            duration_min=recommended.duration_min,
        ),
        progress=progress,
    )


async def seed_lessons(db: AsyncSession) -> None:
    """Insert all 20 CBT lessons if the table is empty."""
    count_stmt = select(func.count()).select_from(CBTLesson)
    count_result = await db.execute(count_stmt)
    count = count_result.scalar_one()

    if count > 0:
        logger.info("seed_lessons_skipped", existing_count=count)
        return

    for data in LESSON_CONTENT:
        lesson = CBTLesson(
            lesson_order=data["lesson_order"],
            title=data["title"],
            content_md=data["content_md"],
            pattern_tags=data["pattern_tags"],
            duration_min=data["duration_min"],
        )
        db.add(lesson)

    await db.flush()
    logger.info("seed_lessons_complete", count=len(LESSON_CONTENT))
