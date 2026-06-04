# App Mobile com Capacitor

Este projeto pode continuar evoluindo como frontend web em Vue e, ao mesmo tempo,
ser empacotado como aplicativo Android com Capacitor.

## Fluxo de desenvolvimento

1. Rodar e ajustar o frontend normalmente.
2. Para Android, gerar o build mobile com `npm.cmd run build:android`.
3. Sincronizar o build com o projeto mobile usando `npm.cmd run cap:sync:android`.
4. Abrir o projeto nativo com `npm.cmd run cap:open:android`.

## URLs da API

- No navegador local, `localhost` funciona normalmente.
- No emulador Android, use `http://10.0.2.2:8000/api/v1`.
- Em celular fisico, use o IP da maquina na rede, por exemplo `http://192.168.0.10:8000/api/v1`.

Use `.env.local` para web local e `.env.android` para o build mobile.

## Passos iniciais

1. Suba a API para a rede local:
   `powershell -ExecutionPolicy Bypass -File .\services\python-api\start-mobile-api.ps1`
2. Instale as dependencias do frontend:
   `npm.cmd install`
3. Gere e sincronize o build Android:
   `npm.cmd run cap:sync:android`
4. Abra no Android Studio:
   `npm.cmd run cap:open:android`
5. No Android Studio, clique em `Run` para abrir no emulador ou celular.

## Atualizando o frontend depois

Voce pode alterar telas, rotas, estilos e componentes quando quiser.
Sempre que houver mudanca no frontend:

1. Rode `npm.cmd run build:android`
2. Rode `npm.cmd run cap:sync:android`

Depois disso, o app Android passa a usar a nova interface.

## Celular fisico

Se for testar em celular fisico, edite `.env.android` e troque `10.0.2.2`
para o IP da sua maquina na rede local, por exemplo `192.168.0.10`.
