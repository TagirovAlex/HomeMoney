import logging
from datetime import date, datetime, timedelta
from calendar import monthrange
from flask import Flask, jsonify, request, render_template, make_response
from data_access.repositories.user_repository import SQLAlchemyUserRepository
from data_access.repositories.transaction_repository import SQLAlchemyTransactionRepository
from data_access.repositories.budget_repository import SQLAlchemyBudgetRepository
from data_access.repositories.income_repository import SQLAlchemyIncomeSourceRepository
from data_access.repositories.saving_repository import SQLAlchemySavingRepository
from data_access.repositories.category_repository import SQLAlchemyCategoryRepository
from services.financial_service import FinancialService
from services.auth_service import AuthService, require_auth, require_csrf, generate_csrf_token, _extract_token, blacklist
from utils.rate_limiter import register_limiter, login_limiter
from utils.env_manager import get_settings, update_settings
from utils.backup_service import BackupService
from utils.bot_manager import start_bot, stop_bot, status_bot, check_proxy
from models.database import Category, Transaction, Budget, IncomeSource
from config import Config
from utils.database_session import get_db

def create_app():
    app = Flask(__name__)

    from utils.database_session import init_db
    with app.app_context():
        init_db()


    user_repo = SQLAlchemyUserRepository()
    transaction_repo = SQLAlchemyTransactionRepository()
    budget_repo = SQLAlchemyBudgetRepository()
    income_repo = SQLAlchemyIncomeSourceRepository()
    saving_repo = SQLAlchemySavingRepository()
    category_repo = SQLAlchemyCategoryRepository()

    financial_service = FinancialService(
        transaction_repo=transaction_repo,
        budget_repo=budget_repo,
        income_repo=income_repo,
        category_repo=category_repo,
    )

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
        if not request.cookies.get("csrf_token"):
            csrf = generate_csrf_token()
            response.set_cookie("csrf_token", csrf, httponly=False, samesite="Lax", max_age=3600, path="/")
        return response

    @app.context_processor
    def inject_now():
        return {"now": datetime.now()}

    # --- Страницы ---

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/transactions')
    def transactions_page():
        return render_template('transactions.html')

    @app.route('/budgets')
    def budgets_page():
        return render_template('budgets.html')

    @app.route('/reports')
    def reports_page():
        today = date.today()
        return render_template('reports.html', current_month=today.month, current_year=today.year)

    @app.route('/admin')
    def admin_page():
        return render_template('admin.html')

    @app.route('/incomes')
    def incomes_page():
        return render_template('incomes.html')

    @app.route('/categories')
    def categories_page():
        return render_template('categories.html')

    @app.route('/savings')
    def savings_page():
        return render_template('savings.html')

    # --- Публичные API ---

    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "service": "Financial Management API", "version": "1.0"})

    @app.route('/api/v1/register', methods=['POST'])
    def register():
        ip = request.remote_addr or "unknown"
        if not register_limiter.is_allowed(f"register:{ip}"):
            retry_after = 300
            return jsonify({"status": "error", "message": f"Слишком много запросов. Попробуйте через {retry_after} секунд."}), 429
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        pw = data['password']
        if len(pw) < 6:
            return jsonify({"status": "error", "message": "Пароль должен быть не менее 6 символов"}), 400
        existing = user_repo.get_by_email(data['email'])
        if existing:
            return jsonify({"status": "error", "message": "Email уже занят"}), 409
        hashed = AuthService.hash_password(data['password'])
        user_data = {
            "email": data['email'],
            "hashed_password": hashed,
            "role": "User",
            "status": "pending",
        }
        if data.get("telegram_id"):
            user_data["telegram_id"] = str(data["telegram_id"])
        user = user_repo.create(user_data)
        return jsonify({"status": "success", "message": "Регистрация выполнена. Дождитесь подтверждения администратором.", "user_id": user.id}), 201

    @app.route('/api/v1/login', methods=['POST'])
    def login():
        ip = request.remote_addr or "unknown"
        log = logging.getLogger(__name__)
        log.debug("login attempt email=%s ip=%s cookies=%s", request.get_json(silent=True).get("email", "?") if request.get_json(silent=True) else "?", ip, list(request.cookies.keys()))
        if not login_limiter.is_allowed(f"login:{ip}"):
            retry_after = 60
            return jsonify({"status": "error", "message": f"Слишком много запросов. Попробуйте через {retry_after} секунд."}), 429
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"status": "error", "message": "email и password обязательны"}), 400
        user = user_repo.get_by_email(data['email'])
        if not user or not AuthService.verify_password(data['password'], user.hashed_password):
            return jsonify({"status": "error", "message": "Неверный email или пароль"}), 401
        if user.status == "pending":
            return jsonify({"status": "error", "message": "Аккаунт ожидает подтверждения администратором."}), 403
        if user.status == "rejected":
            return jsonify({"status": "error", "message": "Аккаунт отклонён."}), 403
        token = AuthService.create_token(user.id, user.role)
        login_limiter.reset(f"login:{ip}")
        response = make_response(jsonify({"status": "success", "token": token, "user": {"id": user.id, "email": user.email, "role": user.role, "status": user.status}}))
        response.set_cookie(
            "auth_token", token,
            httponly=True, samesite="Lax",
            max_age=3600, path="/"
        )
        log.debug("login OK user=%d cookie_set=%s", user.id, [h for h in response.headers.get_all("Set-Cookie")])
        return response

    @app.route('/api/v1/logout', methods=['POST'])
    def logout():
        token = _extract_token()
        if token:
            payload = AuthService.verify_token(token)
            if payload:
                exp = datetime.fromtimestamp(payload["exp"]) if isinstance(payload.get("exp"), (int, float)) else datetime.utcnow() + timedelta(hours=1)
                blacklist.add(payload.get("jti", token), exp)
        response = make_response(jsonify({"status": "success", "message": "Вы вышли из системы."}))
        response.set_cookie("auth_token", "", httponly=True, max_age=0, path="/")
        return response

    # --- Защищённые API ---

    @app.route('/api/v1/me', methods=['GET'])
    @require_auth
    def me():
        logging.getLogger(__name__).debug("me() OK — user=%s", request.current_user)
        return jsonify({"status": "success", "user": request.current_user})

    @app.route('/api/v1/debug/headers', methods=['GET'])
    def debug_headers():
        """Diagnostic endpoint — returns what the server sees."""
        return jsonify({
            "cookies": {k: ("***" if "auth" in k.lower() or "token" in k.lower() else v) for k, v in request.cookies.items()},
            "has_auth_cookie": "auth_token" in request.cookies,
            "has_csrf_cookie": "csrf_token" in request.cookies,
            "is_secure": request.is_secure,
            "scheme": request.scheme,
            "host": request.host,
            "auth_header": ("Bearer ***" if request.headers.get("Authorization", "").startswith("Bearer ") else "none"),
        })

    @app.route('/api/v1/transactions')
    @require_auth
    def list_transactions():
        uid = request.current_user["user_id"]
        today = date.today()
        try:
            summary = financial_service.get_monthly_summary(uid, month=today.month, year=today.year)
            limit = int(Config.DASHBOARD_TX_LIMIT)
            txs, _ = transaction_repo.get_filtered_for_user(uid, page=1, limit=limit)
            all_cats = category_repo.get_all()
            cats = {c.id: {"name": c.name, "icon": c.icon or "📁", "type": c.type or "expense"} for c in all_cats}
            recent = []
            for t in txs:
                cat = cats.get(t.category_id, {"name": f"ID:{t.category_id}", "icon": "📁", "type": "expense"})
                recent.append({
                    "id": t.id,
                    "amount": t.amount,
                    "category_name": cat["name"],
                    "category_icon": cat["icon"],
                    "type": cat["type"],
                    "description": t.description or "",
                    "date": t.date.isoformat() if t.date else "",
                })
            summary["recent_transactions"] = recent
            items = saving_repo.get_by_user(uid)
            summary["total_savings"] = sum(s.amount for s in items)
            return jsonify({"status": "success", "data": summary})
        except Exception:
            logging.exception("list_transactions: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/user/<int:user_id>/transactions/<int:tx_id>', methods=['GET', 'PUT', 'DELETE'])
    @require_auth
    def transaction_detail(user_id, tx_id):
        if request.current_user["user_id"] != user_id and request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Доступ запрещён"}), 403

        if request.method == 'GET':
            with get_db() as session:
                tx = session.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
                if not tx:
                    return jsonify({"status": "error", "message": "Транзакция не найдена"}), 404
                cat = session.query(Category).filter(Category.id == tx.category_id).first()
            return jsonify({"status": "success", "data": {
                "id": tx.id, "amount": tx.amount, "category_id": tx.category_id,
                "category_name": cat.name if cat else "", "category_icon": cat.icon if cat else "",
                "description": tx.description or "", "date": tx.date.isoformat() if tx.date else "",
                "type": getattr(tx, 'type', 'expense'),
            }})

        if request.method == 'DELETE':
            ok = financial_service.delete_transaction(tx_id, user_id)
            if not ok:
                return jsonify({"status": "error", "message": "Транзакция не найдена"}), 404
            return jsonify({"status": "success", "message": "Транзакция удалена"})

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        try:
            financial_service.update_transaction(tx_id, user_id, data)
            return jsonify({"status": "success", "message": "Транзакция обновлена"})
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception:
            logging.exception("transaction_detail: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/user/<int:user_id>/create_transaction', methods=['POST'])
    @require_auth
    def create_transaction_endpoint(user_id):
        if request.current_user["user_id"] != user_id and request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Доступ запрещён"}), 403
        data = request.get_json()
        if not data or 'amount' not in data or 'category_id' not in data:
            return jsonify({"status": "error", "message": "amount и category_id обязательны"}), 400
        try:
            tx = financial_service.add_transaction(
                user_id,
                float(data['amount']),
                int(data['category_id']),
                data.get('description', ''),
                date=data.get('date'),
            )
            return jsonify({"status": "success", "message": "Транзакция добавлена", "transaction_id": tx.id}), 201
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception:
            logging.exception("create_transaction: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/user/<int:user_id>/transactions', methods=['GET'])
    @require_auth
    def user_transactions(user_id):
        if request.current_user["user_id"] != user_id and request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Доступ запрещён"}), 403
        try:
            month = request.args.get('month', type=int)
            year = request.args.get('year', type=int)
            cat = request.args.get('category_id', type=int)
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            result = financial_service.get_filtered_user_transactions(
                user_id, month=month, year=year, category_id=cat, page=page, limit=limit,
                start_date=start_date, end_date=end_date
            )
            return jsonify({"status": "success", "data": result["data"],
                            "total": result["total"], "page": result["page"],
                            "limit": result["limit"], "month": result["month"],
                            "year": result["year"]})
        except Exception:
            logging.exception("user_transactions: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/budgets', methods=['GET'])
    @require_auth
    def list_budgets():
        uid = request.current_user["user_id"]
        budgets = budget_repo.get_all_for_user(uid)
        all_cats = category_repo.get_all()
        cats = {c.id: c.name for c in all_cats}
        cat_icons = {c.id: c.icon or "" for c in all_cats}
        return jsonify({"status": "success", "data": [
            {"id": b.id, "category_id": b.category_id, "category_name": cats.get(b.category_id, f"ID:{b.category_id}"),
             "category_icon": cat_icons.get(b.category_id, ""),
             "target_amount": b.target_amount,
             "period_start": b.period_start_date.isoformat() if b.period_start_date else "",
             "period_end": b.period_end_date.isoformat() if b.period_end_date else ""}
            for b in budgets
        ]})

    @app.route('/api/v1/budgets', methods=['POST'])
    @require_auth
    def create_budget_endpoint():
        data = request.get_json()
        if not data or 'category_id' not in data or 'target_amount' not in data:
            return jsonify({"status": "error", "message": "category_id и target_amount обязательны"}), 400
        try:
            budget = financial_service.create_budget(
                user_id=request.current_user["user_id"],
                category_id=int(data['category_id']),
                target_amount=float(data['target_amount'])
            )
            return jsonify({"status": "success", "message": "Бюджет создан", "budget_id": budget.id}), 201
        except Exception:
            logging.exception("create_budget: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/budgets/<int:budget_id>', methods=['PUT'])
    @require_auth
    def update_budget(budget_id):
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        allowed = {"target_amount", "category_id"}
        update = {k: v for k, v in data.items() if k in allowed}
        if not update:
            return jsonify({"status": "error", "message": "Нет полей для обновления"}), 400
        result = budget_repo.update_budget(budget_id, request.current_user["user_id"], update)
        if not result:
            return jsonify({"status": "error", "message": "Бюджет не найден"}), 404
        cat = category_repo.get_by_id(result.category_id)
        return jsonify({"status": "success", "budget_id": result.id,
                        "category_icon": cat.icon if cat else "",
                        "category_name": cat.name if cat else f"ID:{result.category_id}"})

    @app.route('/api/v1/budgets/<int:budget_id>', methods=['DELETE'])
    @require_auth
    def delete_budget(budget_id):
        ok = budget_repo.delete_budget(budget_id, request.current_user["user_id"])
        if not ok:
            return jsonify({"status": "error", "message": "Бюджет не найден"}), 404
        return jsonify({"status": "success", "message": "Бюджет удалён"})

    @app.route('/api/v1/reports', methods=['GET'])
    @require_auth
    def generate_report():
        uid = request.current_user["user_id"]
        role = request.current_user["role"]
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category_id = request.args.get('category_id', type=int)
        include_tx = request.args.get('include_transactions', '0') in ('1', 'true', 'yes')
        try:
            if start_date and end_date:
                report = financial_service.get_detailed_report(
                    uid, role=role, start_date=start_date, end_date=end_date,
                    category_id=category_id, include_transactions=include_tx)
            else:
                if not month or not year:
                    return jsonify({"status": "error", "message": "Укажите month/year или start_date/end_date"}), 400
                report = financial_service.get_detailed_report(
                    uid, role=role, month=month, year=year,
                    category_id=category_id, include_transactions=include_tx)
            items = saving_repo.get_by_user(uid)
            type_labels = {"deposit": "Депозит", "stocks": "Акции", "bonds": "Облигации", "cash": "Наличные", "other": "Другое"}
            savings_data = []
            total_savings = 0.0
            for s in items:
                total_savings += s.amount
                savings_data.append({
                    "id": s.id, "name": s.name, "amount": s.amount,
                    "type": s.type, "type_label": type_labels.get(s.type, s.type),
                    "description": s.description or "",
                })
            report["savings"] = {"total": round(total_savings, 2), "items": savings_data}
            resp = make_response(jsonify({"status": "success", "data": report}))
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception:
            logging.exception("generate_report: внутренняя ошибка")
            return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500

    @app.route('/api/v1/backup', methods=['GET'])
    @require_auth
    def backup_api():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        svc = BackupService()
        result = svc.create_backup(request.args.get('type', 'full'))
        ok = "Ошибка" not in result
        return jsonify({"status": "success" if ok else "error", "message": result})

    @app.route('/api/v1/users', methods=['GET'])
    @require_auth
    def list_users():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        users = user_repo.get_all(request.current_user["user_id"], request.current_user["role"])
        return jsonify({"status": "success", "data": [{"id": u.id, "email": u.email, "role": u.role, "status": u.status, "telegram_id": u.telegram_id} for u in users]})

    @app.route('/api/v1/users/pending', methods=['GET'])
    @require_auth
    def pending_users():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        users = user_repo.get_pending()
        return jsonify({"status": "success", "data": [{"id": u.id, "email": u.email, "telegram_id": u.telegram_id} for u in users]})

    @app.route('/api/v1/users/<int:user_id>/approve', methods=['POST'])
    @require_auth
    def approve_user(user_id):
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        user = user_repo.update_status(user_id, "active")
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        data = request.get_json()
        if data and data.get("role") in ("User", "Admin"):
            user_repo.update_role(user_id, data["role"])
            return jsonify({"status": "success", "message": f"Пользователь {user.email} подтверждён как {data['role']}"})
        return jsonify({"status": "success", "message": f"Пользователь {user.email} подтверждён"})

    @app.route('/api/v1/users/<int:user_id>/reject', methods=['POST'])
    @require_auth
    def reject_user(user_id):
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        user = user_repo.update_status(user_id, "rejected")
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        return jsonify({"status": "success", "message": f"Пользователь {user.email} отклонён"})

    @app.route('/api/v1/users/<int:user_id>/telegram', methods=['PUT'])
    @require_auth
    def update_user_telegram(user_id):
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        data = request.get_json()
        if not data or "telegram_id" not in data:
            return jsonify({"status": "error", "message": "telegram_id обязателен"}), 400
        user = user_repo.update_telegram_id(user_id, str(data["telegram_id"]))
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        return jsonify({"status": "success", "message": f"Telegram ID для {user.email} обновлён"})

    @app.route('/api/v1/categories', methods=['GET', 'POST'])
    @require_auth
    def categories_api():
        if request.method == 'GET':
            cats = category_repo.get_all()
            return jsonify({"status": "success", "data": [{"id": c.id, "name": c.name, "description": c.description or "", "icon": c.icon or "", "type": c.type or "expense"} for c in cats]})
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        cat = category_repo.create({"name": data['name'], "description": data.get('description', ''), "icon": data.get('icon', ''), "type": data.get('type', 'expense')})
        return jsonify({"status": "success", "category_id": cat.id}), 201

    @app.route('/api/v1/categories/<int:cat_id>', methods=['PUT'])
    @require_auth
    def update_category(cat_id):
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'icon' in data:
            update_data['icon'] = data['icon']
        if 'type' in data:
            update_data['type'] = data['type']
        updated = category_repo.update(cat_id, update_data)
        if not updated:
            return jsonify({"status": "error", "message": "Категория не найдена"}), 404
        return jsonify({"status": "success", "message": "Категория обновлена"})

    @app.route('/api/v1/categories/<int:cat_id>', methods=['DELETE'])
    @require_auth
    def delete_category(cat_id):
        with get_db() as session:
            cat = session.query(Category).filter(Category.id == cat_id).first()
            if not cat:
                return jsonify({"status": "error", "message": "Категория не найдена"}), 404
            tx_count = session.query(Transaction).filter(Transaction.category_id == cat_id).count()
            bg_count = session.query(Budget).filter(Budget.category_id == cat_id).count()
            inc_count = session.query(IncomeSource).filter(IncomeSource.category_id == cat_id).count()
            if tx_count > 0 or bg_count > 0 or inc_count > 0:
                refs = []
                if tx_count: refs.append(f"транзакции ({tx_count})")
                if bg_count: refs.append(f"бюджеты ({bg_count})")
                if inc_count: refs.append(f"доходы ({inc_count})")
                return jsonify({"status": "error", "message": f"Нельзя удалить категорию: есть связанные записи: {', '.join(refs)}"}), 409
            session.delete(cat)
            session.commit()
        return jsonify({"status": "success", "message": "Категория удалена"})

    @app.route('/api/v1/incomes', methods=['GET'])
    @require_auth
    def list_incomes():
        uid = request.current_user["user_id"]
        srcs = income_repo.get_by_user(uid)
        return jsonify({"status": "success", "data": [{
            "id": s.id, "name": s.name, "is_regular": s.is_regular,
            "amount": s.amount, "category_id": s.category_id,
            "description": s.description or "", "period": s.period,
            "day_of_period": s.day_of_period,
            "next_date": s.next_date.isoformat() if s.next_date else None,
            "is_active": s.is_active,
        } for s in srcs]})

    @app.route('/api/v1/incomes', methods=['POST'])
    @require_auth
    def create_income():
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        rec = {
            "user_id": request.current_user["user_id"],
            "name": data['name'],
            "is_regular": data.get('is_regular', True),
            "amount": float(data.get('amount', 0)),
            "category_id": int(data.get('category_id', 1)),
            "description": data.get('description', ''),
            "period": data.get('period', 'monthly'),
            "day_of_period": int(data.get('day_of_period', 1)),
        }
        if rec["is_regular"]:
            today = date.today()
            period = rec["period"]
            dop = rec["day_of_period"]
            if period == "monthly":
                max_day = monthrange(today.year, today.month)[1]
                if dop <= max_day and dop >= today.day:
                    rec["next_date"] = date(today.year, today.month, dop)
                else:
                    m = today.month + 1
                    y = today.year
                    if m > 12:
                        m = 1; y += 1
                    max_day = monthrange(y, m)[1]
                    rec["next_date"] = date(y, m, min(dop, max_day))
            elif period == "weekly":
                days_ahead = dop - today.isoweekday()
                if days_ahead <= 0:
                    days_ahead += 7
                rec["next_date"] = today + timedelta(days=days_ahead)
            else:
                rec["next_date"] = today
        src = income_repo.create(rec)
        return jsonify({"status": "success", "income_id": src.id}), 201

    @app.route('/api/v1/incomes/<int:income_id>', methods=['PUT'])
    @require_auth
    def update_income(income_id):
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        allowed = {"name", "is_regular", "amount", "category_id", "description", "period", "day_of_period", "next_date", "is_active"}
        update = {}
        for k in allowed:
            if k in data:
                v = data[k]
                if k in ("amount",): v = float(v)
                if k in ("category_id", "day_of_period"): v = int(v)
                update[k] = v
        src = income_repo.update(income_id, request.current_user["user_id"], update)
        if not src:
            return jsonify({"status": "error", "message": "Источник дохода не найден"}), 404
        return jsonify({"status": "success", "message": "Источник дохода обновлён"})

    @app.route('/api/v1/incomes/<int:income_id>', methods=['DELETE'])
    @require_auth
    def delete_income(income_id):
        ok = income_repo.delete(income_id, request.current_user["user_id"])
        if not ok:
            return jsonify({"status": "error", "message": "Источник дохода не найден"}), 404
        return jsonify({"status": "success", "message": "Источник дохода удалён"})

    @app.route('/api/v1/incomes/process', methods=['POST'])
    @require_auth
    def process_regular_incomes():
        uid = request.current_user["user_id"]
        result = financial_service.process_regular_payments(uid)
        return jsonify({"status": "success", "data": result})

    @app.route('/api/v1/savings', methods=['GET'])
    @require_auth
    def list_savings():
        uid = request.current_user["user_id"]
        items = saving_repo.get_by_user(uid)
        return jsonify({"status": "success", "data": [{
            "id": s.id, "name": s.name, "amount": s.amount,
            "type": s.type, "description": s.description or "",
            "created_at": s.created_at.isoformat() if s.created_at else "",
        } for s in items]})

    @app.route('/api/v1/savings', methods=['POST'])
    @require_auth
    def create_saving():
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "name обязателен"}), 400
        allowed_types = {"deposit", "stocks", "bonds", "cash", "other"}
        stype = data.get('type', 'deposit')
        if stype not in allowed_types:
            return jsonify({"status": "error", "message": f"Недопустимый тип. Допустимые: {', '.join(sorted(allowed_types))}"}), 400
        rec = {
            "user_id": request.current_user["user_id"],
            "name": data['name'],
            "amount": float(data.get('amount', 0)),
            "type": stype,
            "description": data.get('description', ''),
        }
        obj = saving_repo.create(rec)
        return jsonify({"status": "success", "saving_id": obj.id}), 201

    @app.route('/api/v1/savings/<int:saving_id>', methods=['PUT'])
    @require_auth
    def update_saving(saving_id):
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных"}), 400
        allowed_types = {"deposit", "stocks", "bonds", "cash", "other"}
        allowed = {"name", "amount", "type", "description"}
        update = {}
        for k in allowed:
            if k in data:
                v = data[k]
                if k == "amount": v = float(v)
                if k == "type":
                    if v not in allowed_types:
                        return jsonify({"status": "error", "message": f"Недопустимый тип. Допустимые: {', '.join(sorted(allowed_types))}"}), 400
                update[k] = v
        obj = saving_repo.update(saving_id, request.current_user["user_id"], update)
        if not obj:
            return jsonify({"status": "error", "message": "Накопление не найдено"}), 404
        return jsonify({"status": "success", "message": "Накопление обновлено"})

    @app.route('/api/v1/savings/<int:saving_id>', methods=['DELETE'])
    @require_auth
    def delete_saving(saving_id):
        ok = saving_repo.delete(saving_id, request.current_user["user_id"])
        if not ok:
            return jsonify({"status": "error", "message": "Накопление не найдено"}), 404
        return jsonify({"status": "success", "message": "Накопление удалено"})

    @app.route('/api/v1/admin/settings', methods=['GET', 'PUT'])
    @require_auth
    def admin_settings():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        if request.method == 'GET':
            s = get_settings()
            def _mask(val: str) -> str:
                v = val.strip()
                if not v:
                    return ""
                return "********"
            return jsonify({"status": "success", "data": {
                "HM_BOT_TOKEN": _mask(s.get("HM_BOT_TOKEN", "")),
                "HM_BOT_TOKEN_SET": bool(s.get("HM_BOT_TOKEN", "")),
                "HM_BOT_PROXY_HOST": s.get("HM_BOT_PROXY_HOST", ""),
                "HM_BOT_PROXY_PORT": s.get("HM_BOT_PROXY_PORT", ""),
                "HM_BOT_PROXY_USERNAME": s.get("HM_BOT_PROXY_USERNAME", ""),
                "HM_BOT_PROXY_PASSWORD": _mask(s.get("HM_BOT_PROXY_PASSWORD", "")),
                "HM_BOT_PROXY_PASSWORD_SET": bool(s.get("HM_BOT_PROXY_PASSWORD", "")),
                "HM_BOT_ALLOWED_USERS": s.get("HM_BOT_ALLOWED_USERS", ""),
                "HM_DEBUG": s.get("HM_DEBUG", "false"),
                "HM_DASHBOARD_TX_LIMIT": s.get("HM_DASHBOARD_TX_LIMIT", "5"),
            }})
        data = request.get_json()
        allowed = {"HM_BOT_TOKEN", "HM_BOT_PROXY_HOST", "HM_BOT_PROXY_PORT", "HM_BOT_PROXY_USERNAME", "HM_BOT_PROXY_PASSWORD", "HM_BOT_ALLOWED_USERS", "HM_DEBUG", "HM_DASHBOARD_TX_LIMIT"}
        updates = {}
        current = get_settings()
        for k in allowed:
            if k not in data:
                continue
            v = str(data[k]).strip()
            if not v:
                continue
            if v == "********":
                continue
            updates[k] = v
        if not updates:
            return jsonify({"status": "error", "message": "Нет изменений для сохранения"}), 400
        errors = update_settings(updates)
        if errors:
            return jsonify({"status": "error", "message": "; ".join(errors)}), 500
        return jsonify({"status": "success", "message": "Настройки сохранены. Перезапустите бота/сервер для применения."})

    @app.route('/api/v1/admin/bot/start', methods=['POST'])
    @require_auth
    def bot_start():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        msg = start_bot()
        ok = "Ошибка" not in msg and "уже" not in msg
        return jsonify({"status": "success" if ok else "error", "message": msg})

    @app.route('/api/v1/admin/bot/stop', methods=['POST'])
    @require_auth
    def bot_stop():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        msg = stop_bot()
        return jsonify({"status": "success", "message": msg})

    @app.route('/api/v1/admin/bot/status', methods=['GET'])
    @require_auth
    def bot_status():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        st = status_bot()
        return jsonify({"status": "success", "data": st})

    @app.route('/api/v1/admin/bot/check-proxy', methods=['POST'])
    @require_auth
    def bot_check_proxy():
        if request.current_user["role"] != "Admin":
            return jsonify({"status": "error", "message": "Только для администратора"}), 403
        result = check_proxy()
        return jsonify({"status": "success" if result.get("ok") else "error", "data": result})

    # --- Error handlers ---

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', code=403, message="Доступ запрещён"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message="Страница не найдена"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, message="Внутренняя ошибка сервера"), 500

    return app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        app = create_app()
        logging.info("HomeMoney запущен (Debug=%s)", Config.DEBUG)
        app.run(debug=Config.DEBUG)
    except Exception as e:
        logging.critical("КРИТИЧЕСКАЯ ОШИБКА: %s", e, exc_info=True)
