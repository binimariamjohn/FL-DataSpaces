package com.ionos.edc.provision;

import com.ionos.edc.schema.NextcloudSchema;
import org.eclipse.edc.connector.controlplane.transfer.spi.provision.ConsumerResourceDefinitionGenerator;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcess;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferRequest;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.ResourceDefinition;
import org.eclipse.edc.policy.model.Policy;
import org.jetbrains.annotations.Nullable;
import java.util.Objects;
import static java.util.UUID.randomUUID;

public class NextCloudConsumerResourceDefinitionGenerator  implements ConsumerResourceDefinitionGenerator {




    @Override
    public @Nullable ResourceDefinition generate(TransferProcess transferProcess, Policy policy) {
        Objects.requireNonNull(transferProcess, "dataRequest must always be provided");
        Objects.requireNonNull(policy, "policy must always be provided");

        var id = randomUUID().toString();

        return  NextCloudResourceDefinition.Builder.newInstance()
                .id(id)
                .DataAddress(transferProcess.getDataDestination())
                .build();
    }

    @Override
    public boolean canGenerate(TransferProcess transferProcess, Policy policy) {
        Objects.requireNonNull(transferProcess, "dataRequest must always be provided");
        Objects.requireNonNull(policy, "policy must always be provided");

        return NextcloudSchema.TYPE.equals(transferProcess.getDataDestination().getType());
    }
}
