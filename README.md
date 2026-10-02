# Lambda Consultar Pedido — AWS Community Day Perú 2026

Componente de una demo de asistente de pedidos y devoluciones con **LangChain**,
**Amazon Bedrock** y **AgentCore Gateway**. Esta Lambda consulta el estado y las
fechas de entrega de pedidos ficticios mediante código de pedido y DNI.

## Los tres componentes de la demo

| Proyecto | Función |
|---|---|
| `aws-cd-demo-agente-mcp` | Conversación, conexión con Bedrock y uso de herramientas MCP |
| `aws-cd-demo-api-devoluciones` | Pedidos ficticios, reglas de elegibilidad y cálculo del reembolso estimado |
| `aws-cd-demo-lambda-consultar-pedido` (este repositorio) | Seguimiento del pedido mediante código y DNI: estado y fechas de entrega |

La función recibe y devuelve JSON. Se puede invocar directamente desde la consola
de Lambda, AWS CLI o un SDK, sin API Gateway. El DNI se compara con datos ficticios;
esta comprobación no autentica la identidad de una persona.

## Probar localmente

Con Python 3.12 o superior, sin cuenta AWS ni dependencias adicionales:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas cubren estados de entrega, fechas, formatos de entrada, DNI incorrecto
y pedidos inexistentes.

## Desplegar con SAM

Necesitas una cuenta AWS, [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
[AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
y Python **3.12** para construir el paquete. Configura un perfil con permisos de
despliegue para CloudFormation, S3, Lambda, IAM y CloudWatch Logs, incluido `iam:PassRole`.
Los comandos usan `aws-cd-poc` como ejemplo; sustitúyelo por tu perfil.

Desde la raíz del repositorio:

```powershell
sam validate --lint --template-file template.yaml --region us-east-1
sam build
sam deploy --guided --stack-name aws-cd-demo-pedidos --profile aws-cd-poc --region us-east-1
```

En el asistente, permite la creación del rol IAM y guarda la configuración si deseas
reutilizarla con `sam deploy`. La plantilla crea una Lambda Python 3.12 de 128 MB y
5 segundos de timeout, su rol y un grupo de logs con retención de 7 días. El rol
solo escribe en esos logs. SAM utiliza S3 para almacenar el paquete de despliegue.

El nombre de la función es `<nombre-del-stack>-consultar-pedido`; el stack muestra
`FunctionName` y `FunctionArn` en sus salidas. El despliegue crea recursos para ese
stack: no adopta funciones creadas previamente fuera de CloudFormation.

Opcionalmente, con Docker disponible puedes probar el entorno de Lambda:

```powershell
sam local invoke ConsultarPedidoFunction --event ejemplos/en_transito.json
```

## Consultar sin API Gateway

En la consola de Lambda, abre la función indicada por `FunctionName`, selecciona
**Test** y pega el contenido de uno de los JSON de `ejemplos/`.

Desde PowerShell, para el stack del ejemplo:

```powershell
$funcion = "aws-cd-demo-pedidos-consultar-pedido"
aws lambda invoke --function-name $funcion --profile aws-cd-poc --region us-east-1 --cli-binary-format raw-in-base64-out --payload file://ejemplos/en_transito.json --no-cli-pager respuesta.json
Get-Content -Encoding utf8 respuesta.json
```

La identidad que consulta necesita `lambda:InvokeFunction` sobre esa función.
`StatusCode: 200`, sin `FunctionError`, indica que la ejecución terminó correctamente;
la respuesta de negocio está en `respuesta.json` y puede contener `ok: false`.

Para comprobar todos los casos contra una función desplegada, instala el SDK en un
entorno local; esta dependencia no se incluye en el paquete de Lambda:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.probar_remoto --funcion $funcion --perfil aws-cd-poc --region us-east-1
```

El script guarda sus resultados en `.local/validacion-remota.json`.

## Datos y contrato

El evento exige únicamente dos campos de texto: `pedido_id`, con formato `PED-001`,
y `dni`, con ocho dígitos. Usar texto conserva ceros iniciales.

```json
{"pedido_id": "PED-005", "dni": "12345678"}
```

```json
{
  "ok": true,
  "pedido": {
    "pedido_id": "PED-005",
    "estado": "en_transito",
    "entregado": false,
    "fecha_entrega_estimada": "2026-10-03",
    "fecha_entrega_real": null
  }
}
```

| Pedido | DNI ficticio | Estado | Fecha estimada | Fecha real |
|---|---|---|---|---|
| PED-001 | 12345678 | entregado | — | 2026-09-17 |
| PED-002 | 87654321 | entregado | — | 2026-08-13 |
| PED-003 | 11223344 | entregado | — | 2026-09-25 |
| PED-004 | 12345678 | entregado | — | 2026-09-12 |
| PED-005 | 12345678 | en_transito | 2026-10-03 | — |
| PED-006 | 01234567 | en_preparacion | 2026-10-06 | — |

Los datos representan una situación fija al **2026-10-01**; los estados no cambian
con el reloj. La consulta no modifica pedidos ni devuelve el DNI. Un pedido
inexistente y una combinación incorrecta devuelven `PEDIDO_NO_ENCONTRADO`.
Los demás errores son `ARGUMENTOS_INVALIDOS`, `PEDIDO_ID_INVALIDO` y `DNI_INVALIDO`;
todos tienen la forma `{"ok": false, "error": {"codigo": "...", "mensaje": "..."}}`.

## Archivos

| Archivo | Valor que aporta |
|---|---|
| `src/lambda_function.py` | Valida la entrada y responde con el seguimiento |
| `src/datos.py` | Define los seis pedidos y DNI ficticios |
| `template.yaml` | Declara la Lambda, su rol IAM y los logs con SAM |
| `ejemplos/*.json` | Eventos listos para probar estados y errores |
| `tests/test_lambda_function.py` | Comprueba el contrato sin conectarse a AWS |
| `scripts/probar_remoto.py` | Verifica el comportamiento de la función desplegada |
| `scripts/__init__.py` | Permite ejecutar el script como módulo con `python -m` |
| `requirements.txt` | Instala boto3 únicamente para las pruebas remotas |
| `.gitignore` | Excluye entornos, cachés, paquetes, respuestas y configuración local |

Solo `src/` se empaqueta para Lambda. `.aws-sam/`, `.local/` y `build/` contienen
archivos generados o resultados locales; no forman parte del código que se publica.
