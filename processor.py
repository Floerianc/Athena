import db

log = db.get_logger()

class Processor(db.DBManager):
    def __init__(self, filename: str, insert_json: bool = True) -> None:
        self.filename = filename
        self.json = self._load_data(filename)
        self._validate_json()
        super().__init__()
        
        if insert_json:
            self._insert_json(self.json)
    
    def _validate_json(self) -> None:
        previous_keys = []
        
        for obj in self.json:
            keys = list(obj.keys())
            if not previous_keys:
                previous_keys = keys
            else:
                if previous_keys != keys:
                    raise KeyError("JSON schema must be consistant for every object.")

if __name__ == "__main__":
    pro = Processor(
        "dumps\\test.json",
        insert_json = True
    )