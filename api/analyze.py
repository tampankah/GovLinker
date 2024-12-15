@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
    """
    Validates the document uploaded by the user (JPEG, PNG, or PDF).
    """
    # Validate the file type
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    base64_images = []

    try:
        if file.content_type == "application/pdf":
            # Save the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file.file.read())
                temp_pdf.flush()  # Ensure all data is written to disk
                images = convert_pdf_to_images(temp_pdf.name)  # Convert PDF to images
                base64_images = [pil_image_to_base64(image) for image in images]
        else:
            # Encode image to base64 directly
            base64_image = encode_image_to_base64(file.file)
            base64_images = [base64_image]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")

    # Process each image with the vision model
    results = []
    for image in base64_images:
        result = process_image_with_grok(image) 
        results.append(result)

    # Analyze the aggregated results
    aggregated_result = analyze_document_results(results)
    return aggregated_result

def process_image_with_grok(base64_image: str) -> dict:
    """
    Sends the base64-encoded image to the vision model for analysis.
    """
    try:
        # Send the image to the vision model
        logger.debug("Sending request to Grok Vision model.")
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract and validate all fields in this document match to headlines?",
                        },
                    ],
                }
            ],
        )

        # Log the raw response for debugging purposes
        logger.debug("Received response from Grok Vision model: %s", response)

        # Return the relevant part of the response
        return response.choices[0].message
    except Exception as e:
        # Log any errors that occur during the request
        logger.error("Error while processing image with Grok Vision model: %s", str(e))
        raise

def analyze_document_results_rotmi(results: List[str]) -> DocumentCheckResult:
    """
    Analyzes the results from the vision model by using X.AI API to validate required fields.

    Args:
        results (List[str]): A list of base64-encoded images to analyze.
    
    Returns:
        DocumentCheckResult: The analysis results indicating validity, missing fields, and errors.
    """
    required_fields = ["Name", "Date of Birth", "Document Number", "Expiration Date"]
    missing_fields = []
    errors = []

    if not isinstance(results, list) or not all(isinstance(image, str) for image in results):
        errors.append("Invalid input: 'results' must be a list of base64-encoded image strings.")
        return DocumentCheckResult(is_valid=False, missing_fields=required_fields, errors=errors)

    extracted_fields = []  # Store extracted fields from all images

    try:
        for image in results:
            # Send image to Grok Vision model for analysis
            response = client.chat.completions.create(
                model=VISION_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract all fields present in the document.",
                            },
                        ],
                    }
                ],
            )

            # Extract response content and validate
            vision_output = response.choices[0].message.get("content", {})
            if isinstance(vision_output, dict) and "fields" in vision_output:
                extracted_fields.extend(vision_output["fields"])
            else:
                errors.append("Invalid response from vision model for one of the images.")
    except Exception as e:
        errors.append(f"Error during vision model processing: {str(e)}")
        return DocumentCheckResult(is_valid=False, missing_fields=required_fields, errors=errors)

    # Check for missing required fields
    for field in required_fields:
        if not any(field.lower() in extracted_field.lower() for extracted_field in extracted_fields):
            missing_fields.append(field)

    is_valid = len(missing_fields) == 0

    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)

def analyze_document_results(results: List[str]) -> DocumentCheckResult:
    """
    Analyzes the results from the vision model by using X.AI API to validate required fields
    and assist the user with filling out missing fields.

    Args:
        results (List[str]): A list of base64-encoded images to analyze.

    Returns:
        DocumentCheckResult: The analysis results indicating validity, missing fields, and errors.
    """
    required_fields = ["Name", "Date of Birth", "Document Number", "Expiration Date"]
    missing_fields = []
    errors = []
    filled_fields = []  # This will track the fields that have been filled in correctly

    # Ensure that the input results are a list of base64-encoded images
    if not isinstance(results, list) or not all(isinstance(image, str) for image in results):
        errors.append("Invalid input: 'results' must be a list of base64-encoded image strings.")
        return DocumentCheckResult(is_valid=False, missing_fields=required_fields, errors=errors)

    extracted_fields = []  # Store extracted fields from all images

    try:
        for image in results:
            # Send image to Grok Vision model for analysis
            response = client.chat.completions.create(
                model=VISION_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Process the document extract field and tell me what fields are empty and how to fill them in properly.",
                            },
                        ],
                    }
                ],
            )

            # Extract the response content and validate
            vision_output = response.choices[0].message.get("content", {})
            if isinstance(vision_output, dict) and "fields" in vision_output:
                extracted_fields.extend(vision_output["fields"])
            else:
                errors.append("Invalid response from vision model for one of the images.")
    except Exception as e:
        errors.append(f"Error during vision model processing: {str(e)}")
        return DocumentCheckResult(is_valid=False, missing_fields=required_fields, errors=errors)

    # Check for missing required fields
    for field in required_fields:
        if not any(field.lower() in extracted_field.lower() for extracted_field in extracted_fields):
            missing_fields.append(field)
        else:
            filled_fields.append(field)  # Track fields that were filled in correctly

    # Now, we'll pass the missing fields to the chat model to help the user fill them out
    if missing_fields:
        try:
            # Construct a question for the chat model to help the user fill in the missing fields
            missing_fields_text = ", ".join(missing_fields)
            question = f"The following required fields are missing or incomplete: {missing_fields_text}. Please assist the user in filling out these fields."

            # Create a new agent (chat model) to guide the user through the missing fields
            response = client.chat.completions.create(
                model=CHAT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant helping the user fill out their document."},
                    {"role": "user", "content": question},
                ],
            )

            # Extract the response from the chat model
            guidance_message = response.choices[0].message['content']
            errors.append(guidance_message)  # Add guidance message to errors (could be used for displaying to the user)

        except Exception as e:
            errors.append(f"Error processing with chat model: {str(e)}")

    # Determine if the document is valid
    is_valid = len(missing_fields) == 0

    # Return the results with validity, missing fields, errors, and any additional guidance
    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)
