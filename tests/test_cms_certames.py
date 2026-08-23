from transparencia.collectors.cms_certames import parse_pagination_window, parse_scriptcase_form


def test_parse_pagination_window_uses_server_total() -> None:
    html = """
    <html><body>
      <span>Visualizar</span>
      <div>1 a 10 de 188</div>
      <div>1 a 10 de 188</div>
    </body></html>
    """
    assert parse_pagination_window(html) == (1, 10, 188)


def test_parse_scriptcase_form_reads_dynamic_init_and_fields() -> None:
    html = """
    <form name="F3" method="post" action="./">
      <input type="hidden" name="nmgp_opcao" value="" />
      <input type="hidden" name="nmgp_parms" value="" />
      <input type="hidden" name="script_case_init" value="2976" />
    </form>
    """
    assert parse_scriptcase_form(html) == {
        "nmgp_opcao": "",
        "nmgp_parms": "",
        "script_case_init": "2976",
    }


def test_parse_pagination_window_rejects_invalid_bounds() -> None:
    assert parse_pagination_window("<div>20 a 10 de 188</div>") is None
    assert parse_pagination_window("<div>sem paginação</div>") is None
