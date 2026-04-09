import os
import unicodedata
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy import not_

app = Flask(__name__)

app.secret_key = "segredo123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def normalizar(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower()


# =========================
# MODELOS
# =========================

class Noticia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200))
    resumo = db.Column(db.String(300))
    conteudo = db.Column(db.Text)
    imagem = db.Column(db.String(200))
    categoria = db.Column(db.String(100))
    views = db.Column(db.Integer, default=0)


class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200))


class Denuncia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    mensagem = db.Column(db.Text)


class Onibus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    linha = db.Column(db.String(200))
    saida = db.Column(db.String(50))
    destino = db.Column(db.String(200))
    imagem = db.Column(db.String(200))
    link = db.Column(db.String(300))

class Parceiro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.String(200))
    link = db.Column(db.String(300))  


# =========================
# ROTAS PRINCIPAIS
# =========================

@app.route("/")
def index():

    noticias = Noticia.query.filter(
    not_(Noticia.categoria.in_(["Publicidade", "Vagas"]))
    ).order_by(Noticia.id.desc()).all()

    destaque = noticias[0] if noticias else None

    mais_lidas = Noticia.query.order_by(Noticia.views.desc()).limit(5).all()

    parceiros = Parceiro.query.all()
    
    noticias_mundo = Noticia.query.filter_by(categoria="Mundo").limit(8).all()
   
    vagas = Noticia.query.filter_by(categoria="Vagas").limit(8).all()
   
    return render_template(
        "index.html",
        noticias=noticias,
        destaque=destaque,
        mais_lidas=mais_lidas,
        parceiros=parceiros,
        noticias_mundo=noticias_mundo,
        vagas=vagas
    )


@app.route("/noticia/<int:id>")
def noticia(id):
    noticia = Noticia.query.get(id)
    noticia.views += 1
    db.session.commit()
    return render_template("noticia.html", noticia=noticia)


@app.route("/buscar")
def buscar():
    termo = request.args.get("q")

    resultados = Noticia.query.filter(
        or_(
            Noticia.titulo.contains(termo),
            Noticia.resumo.contains(termo),
            Noticia.conteudo.contains(termo)
        )
    ).all()

    return render_template("busca.html", noticias=resultados, termo=termo)


@app.route("/categoria/<nome_categoria>")
def categoria(nome_categoria):
    categoria_url = normalizar(nome_categoria.replace("-", " "))

    noticias = Noticia.query.all()
    noticias_filtradas = []

    for n in noticias:
        if normalizar(n.categoria) == categoria_url:
            noticias_filtradas.append(n)

    return render_template(
        "categoria.html",
        noticias=noticias_filtradas,
        categoria=nome_categoria.replace("-", " ").title()
    )


@app.route("/anuncie")
def anuncie():
    return render_template("anuncie.html")


# =========================
# DENUNCIA
# =========================

@app.route("/denuncia", methods=["POST"])
def denuncia():
    nome = request.form["nome"]
    mensagem = request.form["mensagem"]

    nova = Denuncia(nome=nome, mensagem=mensagem)
    db.session.add(nova)
    db.session.commit()

    return redirect("/")


@app.route("/denuncia")
def pagina_denuncia():
    return render_template("denuncia.html")


# =========================
# NEWSLETTER
# =========================

@app.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form["email"]

    novo = Newsletter(email=email)
    db.session.add(novo)
    db.session.commit()

    return redirect("/")


# =========================
# ADMIN
# =========================

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        if usuario == "admin" and senha == "1234":
            session["admin"] = True
            return redirect("/admin")

    return render_template("admin_login.html")


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin/login")

    noticias = Noticia.query.all()
    return render_template("admin_dashboard.html", noticias=noticias)

@app.route("/admin/parceiros")
def admin_parceiros():

    if not session.get("admin"):
        return redirect("/admin/login")

    parceiros = Parceiro.query.all()

    return render_template("admin_parceiros.html", parceiros=parceiros)

@app.route("/admin/nova", methods=["GET","POST"])
def admin_nova():
    if not session.get("admin"):
        return redirect("/admin/login")

    if request.method == "POST":
        titulo = request.form["titulo"]
        resumo = request.form["resumo"]
        conteudo = request.form["conteudo"]
        categoria = request.form["categoria"]

        imagem = request.files.get("imagem")
        nome_imagem = ""

        if imagem and imagem.filename != "":
            nome_imagem = secure_filename(imagem.filename)
            caminho = os.path.join("static/uploads", nome_imagem)
            imagem.save(caminho)

        noticia = Noticia(
            titulo=titulo,
            resumo=resumo,
            conteudo=conteudo,
            categoria=categoria,
            imagem=nome_imagem
        )

        db.session.add(noticia)
        db.session.commit()

        return redirect("/admin")

    return render_template("admin_nova.html")


@app.route("/admin/excluir/<int:id>")
def excluir(id):
    noticia = Noticia.query.get(id)
    db.session.delete(noticia)
    db.session.commit()
    return redirect("/admin")


@app.route("/admin/editar/<int:id>", methods=["GET","POST"])
def editar(id):
    if not session.get("admin"):
        return redirect("/admin/login")

    noticia = Noticia.query.get(id)

    if request.method == "POST":
        noticia.titulo = request.form["titulo"]
        noticia.resumo = request.form["resumo"]
        noticia.conteudo = request.form["conteudo"]
        noticia.categoria = request.form["categoria"]

        db.session.commit()
        return redirect("/admin")

    return render_template("admin_editar.html", noticia=noticia)


# =========================
# ADMIN - DENUNCIAS
# =========================

@app.route("/admin/denuncias")
def admin_denuncias():
    if not session.get("admin"):
        return redirect("/admin/login")

    denuncias = Denuncia.query.all()
    return render_template("admin_denuncias.html", denuncias=denuncias)


@app.route("/admin/excluir_denuncia/<int:id>")
def excluir_denuncia(id):
    if not session.get("admin"):
        return redirect("/admin/login")

    denuncia = Denuncia.query.get(id)
    db.session.delete(denuncia)
    db.session.commit()

    return redirect("/admin/denuncias")


@app.route("/admin/denuncia/<int:id>")
def ver_denuncia(id):
    if not session.get("admin"):
        return redirect("/admin/login")

    denuncia = Denuncia.query.get(id)

    return render_template(
        "admin_ver_denuncia.html",
        denuncia=denuncia
    )


@app.route("/admin/emails")
def admin_emails():
    if not session.get("admin"):
        return redirect("/admin/login")

    emails = Newsletter.query.all()
    return render_template("admin_emails.html", emails=emails)


# =========================
# HORÁRIOS DE ÔNIBUS
# =========================

@app.route("/horarios-onibus")
def horarios_onibus():
    horarios = Onibus.query.all()
    return render_template("horarios_onibus.html", horarios=horarios)


@app.route("/admin/onibus")
def admin_onibus():
    if not session.get("admin"):
        return redirect("/admin/login")

    horarios = Onibus.query.all()
    return render_template("admin_onibus.html", horarios=horarios)


@app.route("/admin/onibus/novo", methods=["GET","POST"])
def novo_onibus():
    if not session.get("admin"):
        return redirect("/admin/login")

    if request.method == "POST":
        linha = request.form["linha"]
        saida = request.form["saida"]
        destino = request.form["destino"]
        link = request.form.get("link")

        imagem = request.files.get("imagem")
        nome_imagem = ""

        if imagem and imagem.filename != "":
            nome_imagem = secure_filename(imagem.filename)
            caminho = os.path.join("static/uploads", nome_imagem)
            imagem.save(caminho)

        novo = Onibus(
            linha=linha,
            saida=saida,
            destino=destino,
            imagem=nome_imagem,
            link=link  
)

        db.session.add(novo)
        db.session.commit()

        return redirect("/admin/onibus")

    return render_template("admin_onibus_novo.html")


# =========================
# 🧨 NOVO: EXCLUIR ÔNIBUS
# =========================

@app.route("/deletar-horario/<int:id>", methods=["POST"])
def deletar_horario(id):

    if not session.get("admin"):
        return redirect("/admin/login")

    horario = Onibus.query.get(id)

    if horario:

        # apagar imagem
        if horario.imagem:
            caminho = os.path.join("static/uploads", horario.imagem)
            if os.path.exists(caminho):
                os.remove(caminho)

        db.session.delete(horario)
        db.session.commit()

    return redirect("/admin/onibus")

@app.route("/add-parceiro", methods=["POST"])
def add_parceiro():

    if not session.get("admin"):
        return redirect("/admin/login")

    imagem = request.files.get("imagem")
    link = request.form.get("link")

    nome_imagem = ""

    if imagem and imagem.filename != "":
        nome_imagem = secure_filename(imagem.filename)
        caminho = os.path.join("static/uploads", nome_imagem)
        imagem.save(caminho)

    novo = Parceiro(
        imagem=nome_imagem,
        link=link
    )

    db.session.add(novo)
    db.session.commit()

    return redirect("/admin")

@app.route("/admin/parceiro/excluir/<int:id>")
def excluir_parceiro(id):

    if not session.get("admin"):
        return redirect("/admin/login")

    parceiro = Parceiro.query.get(id)

    if parceiro:

        # 🔥 apagar imagem da pasta
        if parceiro.imagem:
            caminho = os.path.join("static/uploads", parceiro.imagem)
            if os.path.exists(caminho):
                os.remove(caminho)

        db.session.delete(parceiro)
        db.session.commit()

    return redirect("/admin/parceiros")

# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000, debug=True)