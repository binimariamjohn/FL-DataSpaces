package com.ionos.edc.provision;

import java.util.Objects;
import com.ionos.edc.schema.NextcloudSchema;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcess;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.ResourceDefinition;
import org.eclipse.edc.spi.types.domain.DataAddress;

public class NextCloudResourceDefinition extends ResourceDefinition {
    private TransferProcess dataRequest;
    private DataAddress dataAddress;

    private String resourceName;

    public NextCloudResourceDefinition() {

    }

    public TransferProcess getDataRequest() {
        return dataRequest;
    }

    public DataAddress getDataAddress() {
        return dataAddress;
    }

    public String getResourceName() {
        return resourceName;
    }
    @Override
    public Builder toBuilder() {
        return initializeBuilder(new Builder()).DataRequest(dataRequest).DataAddress(dataAddress).ResourceName(resourceName);
    }

    public static class Builder extends ResourceDefinition.Builder<NextCloudResourceDefinition, Builder> {

        private Builder() {
            super(new NextCloudResourceDefinition());
        }

        public static Builder newInstance() {
            return new Builder();
        }

       public Builder DataRequest(TransferProcess dataRequest) {
            resourceDefinition.dataRequest = dataRequest;
            return this;
        }

        public Builder DataAddress(DataAddress dataAddress) {
            resourceDefinition.dataAddress = dataAddress;
            return this;
        }

        public Builder ResourceName(String resourceName) {
            resourceDefinition.resourceName = resourceName;
            return this;
        }
        @Override
        protected void verify() {
            super.verify();
            Objects.requireNonNull(resourceDefinition.dataAddress.getKeyName(), "file path is required");
            Objects.requireNonNull(resourceDefinition.dataRequest.getId(), "file Name is required");
            Objects.requireNonNull(resourceDefinition.dataRequest.getDataDestination(), "Destination is required");
            Objects.requireNonNull(resourceDefinition.dataRequest.getDataDestination().getStringProperty(NextcloudSchema.HTTP_RECEIVER), "Destination Http Receiver is required");
            Objects.requireNonNull(resourceDefinition.dataRequest.getDataDestination().getStringProperty(NextcloudSchema.FILE_PATH), "Destination file path is required");
        }
    }
}
