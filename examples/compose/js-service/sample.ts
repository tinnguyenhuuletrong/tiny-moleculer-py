import { ServiceBroker } from "moleculer"; // install `latest` version
import ioredis from "ioredis"; // install `latest` version

async function main() {
  ioredis;
  // Create a ServiceBroker
  const broker = new ServiceBroker({
    transporter: "redis://localhost:6379",
  });

  // Define a service
  broker.createService({
    name: "math",
    events: {
      async ev_something(ctx) {
        console.log("Recv ev_something from someone !", ctx.params);
      },
    },
    actions: {
      add(ctx) {
        return {
          result: Number(ctx.params.a) + Number(ctx.params.b),
        };
      },

      async random(ctx) {
        const afterMs = ctx.params["afterMs"] || 1000;
        const receiptId = Math.round(Math.random() * Date.now());
        console.log("recieved random request. will emit event after", afterMs);
        setTimeout(async () => {
          console.log(
            "emit success: ",
            await broker.emit("ev_random_number", {
              receiptId,
              value: Math.random(),
            })
          );
        }, afterMs);

        return {
          receiptId: receiptId,
          _note: "ev_random_number will broadcast later with receiptId",
        };
      },

      async callMe(ctx) {
        const remoteActionName = "greeter-py.hello";
        const begin = Date.now();
        const res = await broker.call(
          remoteActionName,
          {
            name: broker.nodeID,
          },
          {
            nodeID: ctx.nodeID || undefined,
          }
        );
        const end = Date.now();

        console.log("attempt to call greeter-py.hello -> ", res);

        return {
          isOk: true,
          info: {
            remoteNode: ctx.nodeID,
            remoteActionName,
            answer: res,
          },
          durationMs: end - begin,
        };
      },
    },
  });

  // Start the broker
  await broker.start();
}
main();
