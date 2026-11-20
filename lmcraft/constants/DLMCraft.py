from typing import Final


class DLMCraft:
    VERSION: Final[str] = "0.0.0"
    CMDB_TYPE: Final[str] = "application"
    CMDB_SUBTYPE: Final[str] = "LambdaMOO world server"
    CMDB_SUPPLIER: Final[str] = "Nadim-Daniel"
    CMDB_CODENAME: Final[str] = "Initial LambdaMOO deployment"
    CMDB_COMPONENTS = (("MOO world database", "data"), ("Configuration", "conf"))
    CMDB_DATABASES = ()
    CMDB_NETWORK = (("MOO clients", "0.0.0.0", 3333),)
    BASE_DIR: Final[str] = "/opt/prod/lmcraft"
