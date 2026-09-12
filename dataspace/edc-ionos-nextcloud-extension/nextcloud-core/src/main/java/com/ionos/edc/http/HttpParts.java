package com.ionos.edc.http;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonTypeName;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.annotation.JsonPOJOBuilder;
import com.ionos.edc.token.NextCloudToken;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcess;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.spi.types.domain.DataAddress;

@JsonTypeName("dataspaceconnector:httpParts")
@JsonDeserialize(builder = HttpParts.Builder.class)
public class HttpParts {
    private DataAddress dataAddress;
    private DataAddress dataRequest;

    private NextCloudToken url;
    private Policy policy;
    private String transferProcessId;
    private String processId;
    private String resourceDefinitionId;
    private String assetId;



    public HttpParts() {

    }

    public DataAddress getDataAddress() {
        return dataAddress;
    }

    public DataAddress getDataRequest() {
        return dataRequest;
    }

    public NextCloudToken getUrl() {
        return url;
    }

    public String getAssetId() {
        return assetId;
    }

    public String getTransferProcessId() {
        return transferProcessId;
    }

    public String getProcessId() { return processId; }

    public void setProcessId(String processId) {
        this.processId = processId;
    }

    public Policy getPolicy() {
        return policy;
    }

    public String getResourceDefinitionId() {
        return resourceDefinitionId;
    }


    public enum Type {
        @JsonProperty("provision")
        PROVISION,

        @JsonProperty("deprovision")
        DEPROVISION
    }
    
    @JsonPOJOBuilder(withPrefix = "")
    public static class Builder {
        private final HttpParts request;

        private Builder() {
            request = new HttpParts();
        }

        @JsonCreator
        public static Builder newInstance() {
            return new Builder();
        }

        public Builder dataAddress(DataAddress dataAddress) {
            request.dataAddress = dataAddress;
            return this;
        }

        public Builder dataRequest(DataAddress dataRequest) {
            request.dataRequest = dataRequest;
            return this;
        }

        public Builder url(NextCloudToken url) {
            request.url = url;
            return this;
        }
        public Builder assetId(String assetId) {
            request.assetId = assetId;
            return this;
        }

        public Builder transferProcessId(String transferProcessId) {
            request.transferProcessId = transferProcessId;
            return this;
        }
        public Builder processId(String processId) {
            request.processId = processId;
            return this;
        }

        public Builder policy(Policy policy) {
            request.policy = policy;
            return this;
        }


        public Builder resourceDefinitionId(String resourceDefinitionId) {
            request.resourceDefinitionId = resourceDefinitionId;
            return this;
        }



        public HttpParts build() {
            return request;
        }
    }
}
