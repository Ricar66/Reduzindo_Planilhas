# app/helpers/padronizador.
import unicodedata

def _simplificar_texto(texto: str) -> str:
    """Função interna para limpar e normalizar um texto para comparação."""
    if not texto:
        return ""
    # Converte para minúsculas
    texto = texto.lower()
    # Remove acentos
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    # Remove caracteres não alfanuméricos (espaços, hífens, etc.)
    texto = "".join(c for c in texto if c.isalnum())
    return texto

def encontrar_filial_correspondente(texto_da_planilha: str, lista_oficial_filiais: list[str]) -> str:
    """
    Compara um texto de filial (da planilha) com a lista oficial e retorna a correspondência correta.
    """
    if not texto_da_planilha or not lista_oficial_filiais:
        return texto_da_planilha # Retorna o original se a entrada for vazia

    texto_simplificado = _simplificar_texto(texto_da_planilha)

    # 1ª Tentativa: Busca por correspondência exata (após simplificação)
    for filial_oficial in lista_oficial_filiais:
        if _simplificar_texto(filial_oficial) == texto_simplificado:
            return filial_oficial # Encontrou! Retorna o nome oficial.

    # 2ª Tentativa: Busca parcial (se o texto da planilha está contido no nome oficial)
    # Isso resolve casos como "Rio Preto" contido em "01-Rio Preto"
    for filial_oficial in lista_oficial_filiais:
        if texto_simplificado in _simplificar_texto(filial_oficial):
            return filial_oficial # Encontrou! Retorna o nome oficial.

    # Se não encontrar nenhuma correspondência, retorna o texto original da planilha
    return texto_da_planilha