from .extensions import db


class HSBatch(db.Model):
    __tablename__ = 'hs_batch'

    batch_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    import_time = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    # 关系：一个 batch 可以包含多个 image
    images = db.relationship('HSImage', backref='batch', lazy='dynamic')

    def get_batch_size(self):
        return self.images.count()

    def get_batch_status(self):
        if self.images.filter(HSImage.detect_time.is_(None)).count() > 0:
            return 'unfinished'
        else:
            return 'finished'


class HSImage(db.Model):
    __tablename__ = 'hs_image'

    image_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_original_path = db.Column(db.String(255), nullable=False)
    image_processed_path = db.Column(db.String(255), nullable=True)
    detect_time = db.Column(db.DateTime, nullable=True)
    create_time = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)

    # 外键，关联到 batch 表
    batch_id = db.Column(db.Integer, db.ForeignKey('hs_batch.batch_id'), nullable=False)

    # 关系：一张图片可以包含多个缺陷（Defect）
    defects = db.relationship('HSDefect', backref='image', lazy='dynamic')


class HSDefect(db.Model):
    __tablename__ = 'hs_defect'

    defect_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    defect_type = db.Column(db.String(50), nullable=False)

    bbox = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)

    # 外键，关联到 image 表
    image_id = db.Column(db.Integer, db.ForeignKey('hs_image.image_id'), nullable=False)


class HSReport(db.Model):
    __tablename__ = 'hs_report'

    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_time = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    report_file_path = db.Column(db.String(255), nullable=True)
