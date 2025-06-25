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
    actions: {
      add(ctx) {
        return {
          result: Number(ctx.params.a) + Number(ctx.params.b),
        };
      },
    },
  });

  // Start the broker
  await broker.start();
}
main();
