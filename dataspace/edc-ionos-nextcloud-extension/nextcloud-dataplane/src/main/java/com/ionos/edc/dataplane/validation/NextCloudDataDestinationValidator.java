package com.ionos.edc.dataplane.validation;

import com.ionos.edc.schema.NextcloudSchema;
import org.eclipse.edc.spi.types.domain.DataAddress;
import org.eclipse.edc.util.string.StringUtils;
import org.eclipse.edc.validator.spi.ValidationResult;
import org.eclipse.edc.validator.spi.Validator;
import org.eclipse.edc.validator.spi.Violation;

public class NextCloudDataDestinationValidator implements Validator<DataAddress> {
    
    @Override
    public ValidationResult validate(DataAddress input) {
        if (StringUtils.isNullOrBlank(input.getStringProperty(NextcloudSchema.FILE_PATH, null))) {
            return ValidationResult.failure(Violation.violation("Must contain property '%s'".formatted(NextcloudSchema.FILE_PATH), NextcloudSchema.FILE_PATH));
        }
        if (StringUtils.isNullOrBlank(input.getStringProperty(NextcloudSchema.HTTP_RECEIVER, null))) {
            return ValidationResult.failure(Violation.violation("Must contain property '%s'".formatted(NextcloudSchema.HTTP_RECEIVER), NextcloudSchema.FILE_NAME));
        }
        return ValidationResult.success();
    }
}
