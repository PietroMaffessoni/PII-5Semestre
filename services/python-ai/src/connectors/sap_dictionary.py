from dataclasses import dataclass


@dataclass
class SapTableDefinition:
    name: str
    description: str
    module: str


def load_dictionary_stub() -> list[SapTableDefinition]:
    return [
        SapTableDefinition(name="MSEG", description="Documento de material", module="MM"),
        SapTableDefinition(name="VBRK", description="Cabecalho de faturamento", module="SD"),
        SapTableDefinition(name="AFKO", description="Ordens de producao", module="PP"),
    ]
