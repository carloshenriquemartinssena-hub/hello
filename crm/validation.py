"""Mensagens de validação sem incluir os valores recebidos."""
LABELS = {'name': 'Nome', 'email': 'Email', 'phone': 'Telefone', 'sender': 'Remetente',
          'sender_name': 'Nome do remetente', 'start_date': 'Início', 'end_date': 'Validade',
          'templates': 'Mensagens', 'subject': 'Assunto', 'body': 'Texto', 'intervals': 'Intervalos',
          'cta_url': 'Link da proposta', 'city': 'Cidade', 'niche': 'Nicho'}


def validation_summary(errors):
    messages = []
    for error in errors[:8]:
        location = list(error.get('loc', ()))
        if location and location[0] in {'body', 'query', 'path'}:
            location = location[1:]
        field = ' → '.join(str(x + 1) if isinstance(x, int) else LABELS.get(x, str(x)) for x in location)
        kind = error.get('type', '')
        message = str(error.get('msg', 'Revise o campo.')).removeprefix('Value error, ')
        if kind == 'missing': message = 'Preencha este campo.'
        elif kind == 'string_too_short': message = 'O texto está vazio ou curto demais.'
        elif kind == 'string_too_long': message = 'O texto excede o limite permitido.'
        elif kind in {'int_parsing', 'int_type', 'greater_than_equal', 'less_than_equal'}: message = 'Use um número dentro do intervalo permitido.'
        elif kind in {'date_parsing', 'date_from_datetime_parsing'}: message = 'Use uma data válida.'
        detail = (field + ': ' if field else '') + message
        if detail not in messages:
            messages.append(detail)
    return '\n'.join(messages) or 'Revise os campos preenchidos.'
