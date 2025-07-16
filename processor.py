import db

log = db.get_logger()

class Processor:
    def __init__(self, db: db.DBManager, filename: str, insert_json: bool = True) -> None:
        self.db_manager = db
        self.filename = filename
        self.json = self.db_manager._load_data(filename)
        self._validate_json()
        super().__init__()
        
        if insert_json:
            self.db_manager._insert_json(self.json)
    
    def _validate_json(self) -> None:
        previous_keys = []
        
        for obj in self.json:
            keys = list(obj.keys())
            if not previous_keys:
                previous_keys = keys
            else:
                if previous_keys != keys:
                    raise KeyError("JSON schema must be consistant for every object.")