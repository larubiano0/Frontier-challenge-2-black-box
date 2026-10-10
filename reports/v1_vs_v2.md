| n | request | respuesta v1 (histórica) | respuesta v2 (observada) | ¿igual? | diferencias (descriptivo) |
|---|---|---|---|---|---|
| 1 | `{"m":"PING;64"}` | 200 `{"pong":true}` | 200 `{"pong":true}` | sí |  |
| 2 | `{"m":"ALTA;Lucia;83"}` | 400 `{"error":"E202","mensaje":"control inválido"}` | 400 `{"error":"E202","mensaje":"control inválido"}` | sí |  |
| 3 | `{"m":"ALTA;Lucia;82"}` | 201 `{"cuentaId":"AC-0001"}` | 201 `{"cuentaId":"AC-0001"}` | sí |  |
| 4 | `{"m":"ALTA;Mateo;3"}` | 201 `{"cuentaId":"AC-0002"}` | 201 `{"cuentaId":"AC-0002"}` | sí |  |
| 5 | `{"m":"CONSULTA;AC-0001;14"}` | 200 `{"cuenta_id":"AC-0001","saldo":0}` | 200 `{"cuenta_id":"AC-0001","saldo":"0.00"}` | **NO** (candidata) | $.saldo: 0 (int) → "0.00" (str) |
| 6 | `{"m":"DEPOSITO;AC-0001;250000;86"}` | 200 `{"status":"recieved","operacionId":"OP-0001"}` | 200 `{"status":"recieved","operacionId":"OP-0001"}` | sí |  |
| 7 | `{"m":"TRANSFER;AC-0001;AC-0002;40000;86"}` | 200 `{"status":"recieved","operacionId":"OP-0002"}` | 200 `{"status":"recieved","operacionId":"OP-0002"}` | sí |  |
| 8 | `{"m":"CONSULTA;AC-0002;11"}` | 200 `{"cuenta_id":"AC-0002","saldo":40000}` | 200 `{"cuenta_id":"AC-0002","saldo":"400.00"}` | **NO** (candidata) | $.saldo: 40000 (int) → "400.00" (str) |
| 9 | `{"m":"TRANSFER;AC-0001;AC-0002;120000;55"}` | 422 `{"error":"E506","mensaje":"límite excedido"}` | 422 `{"error":"E506","mensaje":"límite excedido"}` | sí |  |
| 10 | `{"m":"TRANSFER;AC-0001;AC-0002;100000;12"}` | 200 `{"status":"recieved","operacionId":"OP-0003"}` | 422 `{"error":"E506","mensaje":"límite excedido"}` | **NO** (candidata) | status 200 → 422; $.error: (ausente) → "E506"; $.mensaje: (ausente) → "límite excedido"; $.operacionId: "OP-0003" → (ausente); $.status: "recieved" → (ausente) |
| 11 | `{"m":"CONSULTa;AC-0001;14"}` | 200 `{"cuenta_id":"AC-0001","saldo":110000}` | 200 `{"cuenta_id":"AC-0001","saldo":"2100.00"}` | **NO** (candidata) | $.saldo: 110000 (int) → "2100.00" (str) |
| 12 | `{"m":"SALDOS;AC-0001;38"}` | 400 `{"error":"E301","mensaje":"comando desconocido "}` | 400 `{"error":"E301","mensaje":"comando desconocido "}` | sí |  |
| 13 | `{"m":"ANULA;OP-0003;66"}` | 200 `{"ok":true,"anulada":"OP-0003"}` | 404 `{"error":"E402","mensaje":"operación inexistente"}` | **NO** (candidata) | status 200 → 404; $.anulada: "OP-0003" → (ausente); $.error: (ausente) → "E402"; $.mensaje: (ausente) → "operación inexistente"; $.ok: true → (ausente) |
| 14 | `{"m":"ANULA;OP-0003;66"}` | 200 `{"ok":false,"motivo":"ya anulada"}` | 404 `{"error":"E402","mensaje":"operación inexistente"}` | **NO** (candidata) | status 200 → 404; $.error: (ausente) → "E402"; $.mensaje: (ausente) → "operación inexistente"; $.motivo: "ya anulada" → (ausente); $.ok: false → (ausente) |
| 15 | `{"m":"CONSULTA;AC-0009;87"}` | 404 `{"error":"E401","mensaje":"cuenta inexistente"}` | 404 `{"error":"E401","mensaje":"cuenta inexistente"}` | sí |  |
| 16 | `{"m":"TRANSFER;AC-0002;AC-0001;50000;23"}` | 422 `{"error":"E507","mensaje":"saldo insuficiente"}` | 422 `{"error":"E507","mensaje":"saldo insuficiente"}` | sí |  |
| 17 | `{"m":"DEPOSITO;AC-0002;700;5X"}` | 400 `{"error":"E201","mensaje":"control mal formado"}` | 400 `{"error":"E201","mensaje":"control mal formado"}` | sí |  |
| 18 | `{"m":"DEPOSITO;AC-0002;700;35"}` | 200 `{"status":"recieved","operacionId":"OP-0004"}` | 200 `{"status":"recieved","operacionId":"OP-0003"}` | **NO** (candidata) | $.operacionId: "OP-0004" → "OP-0003" |
| 19 | `{"m":"CONSULTA;AC-0002;11"}` | 200 `{"cuenta_id":"AC-0002","saldo":40700}` | 200 `{"cuenta_id":"AC-0002","saldo":"407.00"}` | **NO** (candidata) | $.saldo: 40700 (int) → "407.00" (str) |
| 20 | `{"m":"ALTA;Lucia;Gomez;11"}` | 400 `{"error":"E302","mensaje":"aridad inválida"}` | 400 `{"error":"E302","mensaje":"aridad inválida"}` | sí |  |

Pasos: 20; iguales: 12; distintos (candidatas): 8. Fuentes v2: ids 2–21 de experimentos.jsonl; v1: pruebas/ejemplos.jsonl (no está en el log).
